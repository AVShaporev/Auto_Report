"""Подпись заказчика под отчётом (этап 1.2).

Заказчик расписывается пальцем на телефоне инженера. Приходит data URL PNG в
`customer_signature` при создании или изменении отчёта (так подпись едет через
офлайн-очередь мобилки вместе с отчётом). Храним PNG в MEDIA/reports/<id>/,
в таблице — путь, ФИО, должность, время. В акт — {{ customer_signature }}.
"""
from __future__ import annotations

import base64
import binascii
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from config import MEDIA_PATH
from model.report import Report
from schema.report import CustomerSignatureIn

MAX_BYTES = 400 * 1024
MAX_WIDTH = 1600
APPROVED_STATUS_NAME = "Утверждён"


def signature_file(report: Report) -> Optional[Path]:
    if not report.signature_path:
        return None
    p = MEDIA_PATH / report.signature_path
    return p if p.exists() else None


def _decode_png(data: str) -> bytes:
    raw = data.split(",", 1)[1] if data.startswith("data:") else data
    try:
        content = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Подпись: картинка повреждена")
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="Подпись: картинка больше 400 КБ")
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Подпись: нужен PNG")
    if img.format != "PNG":
        raise HTTPException(status_code=400, detail="Подпись: нужен PNG")
    # Прозрачный фон → белый (в Word прозрачность местами печатается чёрной),
    # лишнее поле вокруг росчерка обрезаем, ширину ограничиваем.
    rgba = img.convert("RGBA")
    ground = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(ground, rgba).convert("L")
    ink = flat.point(lambda v: 255 if v < 200 else 0).getbbox()
    if not ink:
        raise HTTPException(status_code=400, detail="Подпись пустая — распишитесь ещё раз")
    pad = 12
    box = (max(ink[0] - pad, 0), max(ink[1] - pad, 0),
           min(ink[2] + pad, flat.width), min(ink[3] + pad, flat.height))
    out = flat.crop(box)
    if out.width > MAX_WIDTH:
        out = out.resize((MAX_WIDTH, round(out.height * MAX_WIDTH / out.width)), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def ensure_not_approved(report: Report) -> None:
    status = getattr(report, "status", None)
    if status is not None and status.name == APPROVED_STATUS_NAME:
        raise HTTPException(status_code=400, detail="Отчёт утверждён — подпись изменить нельзя")


def clear_signature(report: Report) -> None:
    old = signature_file(report)
    report.signature_path = None
    report.signer_name = None
    report.signer_position = None
    report.signed_at = None
    if old:
        old.unlink(missing_ok=True)


def save_signature(report: Report, sig: CustomerSignatureIn) -> None:
    """Проверить и записать подпись в отчёт (commit — на вызывающем)."""
    png = _decode_png(sig.image)
    rel = Path("reports") / str(report.id) / f"signature_{uuid.uuid4().hex[:12]}.png"
    target = MEDIA_PATH / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(png)
    old = signature_file(report)
    report.signature_path = rel.as_posix()
    report.signer_name = sig.signer_name.strip()
    report.signer_position = (sig.signer_position or "").strip() or None
    signed = sig.signed_at or datetime.now(timezone.utc)
    report.signed_at = signed if signed.tzinfo else signed.replace(tzinfo=timezone.utc)
    if old and old != target:
        old.unlink(missing_ok=True)
