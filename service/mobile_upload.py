"""Mobile M1.5 — chunked upload assembly + Pillow resize.

Design:
  - Клиент: init → PUT chunks with Content-Range → GET status → готово.
  - Сервер держит session-row + tmp-файл в MEDIA_PATH/mobile/tmp/<upload_id>.part.
  - При received_bytes == total_size → assemble: Pillow open → resize
    (max 2000px, JPEG q=80) → move в MEDIA_PATH/mobile/<final_name>.

Ограничения:
  - MAX_UPLOAD_SIZE = 50 MB (защита от wall-of-photos).
  - MAX_CHUNK_SIZE = 5 MB.
  - Session TTL = 1 час (клиент должен успеть за это время).
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from config import MEDIA_PATH
from data import media_upload_session as upload_data
from database.database import new_session
from model.media_upload_session import MediaUploadSession

logger = logging.getLogger(__name__)


MAX_UPLOAD_SIZE = 50 * 1024 * 1024   # 50 MB
MAX_CHUNK_SIZE = 5 * 1024 * 1024     # 5 MB
SESSION_TTL_HOURS = 1
MOBILE_ROOT = MEDIA_PATH / "mobile"
TMP_ROOT = MOBILE_ROOT / "tmp"
MAX_IMAGE_DIMENSION = 2000
JPEG_QUALITY = 80

# Content-Range: bytes 0-262143/1048576
_RANGE_RE = re.compile(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$")


class UploadError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _ensure_dirs() -> None:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    MOBILE_ROOT.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str) -> str:
    """Санитайз для final-имени. Разрешаем a-z0-9._-, остальное → _."""
    name = os.path.basename(name)
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return clean[:200] or "upload"


async def init_upload_session(
    *, user_name: str, kind: str, filename: str, total_size: int
) -> MediaUploadSession:
    if total_size <= 0 or total_size > MAX_UPLOAD_SIZE:
        raise UploadError(
            f"total_size must be 1..{MAX_UPLOAD_SIZE} bytes",
            status_code=413,
        )
    _ensure_dirs()

    upload_id = uuid.uuid4().hex
    tmp_path = TMP_ROOT / f"{upload_id}.part"
    tmp_path.write_bytes(b"")  # создаём пустой файл сразу

    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)

    async with new_session() as session:
        row = await upload_data.create_media_upload_session(
            session,
            upload_id=upload_id,
            user_name=user_name,
            kind=kind,
            filename=_safe_filename(filename),
            total_size=total_size,
            tmp_path=str(tmp_path),
            expires_at=expires_at,
        )
    return row


def _parse_content_range(header: str, total_size: int) -> Tuple[int, int]:
    """Возвращает (start, end_inclusive). Проверяет что total совпадает."""
    m = _RANGE_RE.match(header.strip())
    if not m:
        raise UploadError("Invalid Content-Range header")
    start, end, total = m.group(1), m.group(2), m.group(3)
    start_i, end_i = int(start), int(end)
    if total != "*" and int(total) != total_size:
        raise UploadError("Content-Range total mismatch")
    if start_i < 0 or end_i < start_i:
        raise UploadError("Content-Range out of order")
    if (end_i - start_i + 1) > MAX_CHUNK_SIZE:
        raise UploadError(
            f"chunk too big (max {MAX_CHUNK_SIZE} bytes)",
            status_code=413,
        )
    return start_i, end_i


async def append_chunk(
    *,
    upload_id: str,
    user_name: str,
    content_range: str,
    chunk_bytes: bytes,
) -> MediaUploadSession:
    """Append chunk_bytes к tmp-файлу session'а. Возвращает обновлённый
    row (received_bytes инкрементирован). НЕ финализирует."""
    async with new_session() as session:
        row = await upload_data.get_media_upload_session(session, upload_id)
        if row is None:
            raise UploadError("upload session not found", status_code=404)
        if row.user_name != user_name:
            raise UploadError("access denied", status_code=403)
        if row.is_complete:
            raise UploadError("upload already complete", status_code=409)
        if row.expires_at < datetime.now(timezone.utc).replace(tzinfo=row.expires_at.tzinfo):
            raise UploadError("upload session expired", status_code=410)

        start, end = _parse_content_range(content_range, row.total_size)
        expected_end = row.received_bytes - 1
        if start != row.received_bytes:
            raise UploadError(
                f"chunk out of order: expected start={row.received_bytes}, got {start}",
                status_code=416,
            )
        if (end - start + 1) != len(chunk_bytes):
            raise UploadError(
                f"chunk size mismatch: header says {end-start+1}, body {len(chunk_bytes)}",
            )
        if end + 1 > row.total_size:
            raise UploadError(
                f"chunk exceeds total_size ({end+1} > {row.total_size})",
                status_code=413,
            )

        tmp_path = Path(row.tmp_path)
        with tmp_path.open("ab") as f:
            f.write(chunk_bytes)

        new_received = row.received_bytes + len(chunk_bytes)
        await upload_data.update_media_upload_progress(
            session, row, received_bytes=new_received,
        )

    return row


async def finalize_if_complete(*, upload_id: str) -> Optional[MediaUploadSession]:
    """Если received == total, resize + move в final_path. Возвращает
    обновлённый row либо None если ещё не готово."""
    async with new_session() as session:
        row = await upload_data.get_media_upload_session(session, upload_id)
        if row is None or row.is_complete:
            return row
        if row.received_bytes < row.total_size:
            return None

        tmp_path = Path(row.tmp_path)
        if not tmp_path.exists():
            raise UploadError("tmp file missing", status_code=500)

        # Resize через Pillow — предполагаем JPEG/PNG/HEIC (heif через
        # pillow-heif). Если файл не картинка — save as-is.
        final_name = f"{uuid.uuid4().hex}_{row.filename}"
        final_path = MOBILE_ROOT / final_name

        try:
            with Image.open(tmp_path) as img:
                # EXIF-orientation учитываем.
                try:
                    from PIL import ImageOps
                    img = ImageOps.exif_transpose(img)
                except Exception:  # noqa: BLE001
                    pass
                img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
                # Всегда пишем в JPEG (компактнее HEIC/PNG).
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                # Заменяем расширение на .jpg.
                final_path = final_path.with_suffix(".jpg")
                img.save(final_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "mobile upload %s: Pillow failed (%s) — saving as-is", upload_id, e
            )
            # Не картинка (docx/pdf/аудио) — переносим as-is.
            tmp_path.replace(final_path)

        # Удаляем tmp, если он всё ещё есть (Pillow save обычно оставляет исходник).
        if tmp_path.exists() and tmp_path != final_path:
            try:
                tmp_path.unlink()
            except OSError:
                pass

        # Относительный path относительно MEDIA_PATH — чтобы клиент мог
        # склеить с MEDIA_URL или отдать в issue_attachment.
        rel_path = str(final_path.relative_to(MEDIA_PATH))
        await upload_data.finalize_media_upload_session(
            session, row, final_path=rel_path,
        )

    return row


async def cleanup_stale_sessions_and_files() -> tuple[int, int]:
    """Раз в сутки. Возвращает (deleted_sessions, deleted_tmp_files).
    Не трогает completed session'ы (они хранят ссылку на реальный файл в media)."""
    async with new_session() as session:
        tmp_paths = await upload_data.cleanup_expired_media_upload_sessions(session)

    removed = 0
    for p in tmp_paths:
        try:
            path = Path(p)
            if path.exists():
                path.unlink()
                removed += 1
        except OSError:
            pass

    # Заодно снесём orphan tmp-файлы старше 24ч, у которых нет row в БД.
    _ensure_dirs()
    now_ts = datetime.now(timezone.utc).timestamp()
    orphan = 0
    for f in TMP_ROOT.iterdir():
        try:
            if f.is_file() and (now_ts - f.stat().st_mtime) > 24 * 3600:
                f.unlink()
                orphan += 1
        except OSError:
            pass
    return len(tmp_paths), removed + orphan
