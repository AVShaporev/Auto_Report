"""
Бизнес-логика работы с вложениями отчёта (PDF, сконвертированные из фото).
"""
import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile

from config import MEDIA_PATH
from data import report as report_data
from data import report_attachment as attachment_data
from database.database import new_session
from model.report_attachment import Report_Attachment
from model.user import User
from schema.report_attachment import ReportAttachmentKind
from service.attachment_converter import (
    convert_disk_files_to_pdf,
    convert_uploads_to_pdf,
)


# ========== УТИЛИТЫ ==========

def _check_permission(current_user: User, permission: str, action: str) -> None:
    if not hasattr(current_user.role, permission):
        raise HTTPException(
            status_code=500,
            detail=f"Право {permission} не определено в системе",
        )
    if not getattr(current_user.role, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Недостаточно прав для {action}",
        )


def _slugify(value: str, fallback: str) -> str:
    """Простой ASCII-slug для имени файла."""
    value = (value or "").strip()
    if not value:
        return fallback
    # Транслит делать не будем — просто оставим латиницу/цифры/-/_, остальное в '_'
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return cleaned[:60] or fallback


def _attachment_filename(attachment_id: int, kind: str, title: Optional[str]) -> str:
    slug = _slugify(title or "", fallback=kind)
    return f"{attachment_id}_{slug}.pdf"


def _report_dir(report_id: int) -> Path:
    return MEDIA_PATH / "reports" / str(report_id)


def _abs_path(rel_path: str) -> Path:
    return MEDIA_PATH / rel_path


def _to_response(att: Report_Attachment) -> dict:
    return {
        "id": att.id,
        "report_id": att.report_id,
        "kind": att.kind,
        "title": att.title,
        "size_bytes": att.size_bytes,
        "pages": att.pages,
        "created_at": att.created_at,
        "uploaded_by": att.uploaded_by,
        "uploader_name": att.uploader.name if att.uploader else None,
    }


# ========== ПОЛУЧЕНИЕ ==========

async def list_attachments(report_id: int, current_user: User) -> List[dict]:
    _check_permission(current_user, "report_read", "просмотра вложений отчёта")
    async with new_session() as session:
        report = await report_data.get_report_by_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Отчёт с id {report_id} не найден")
        items = await attachment_data.get_report_attachment_by_report(session, report_id)
        return [_to_response(item) for item in items]


async def get_attachment_for_download(
    report_id: int,
    attachment_id: int,
    current_user: User,
) -> Tuple[Path, str]:
    """Вернуть (абсолютный_путь_к_файлу, имя_для_отдачи)."""
    _check_permission(current_user, "report_read", "скачивания вложений отчёта")
    async with new_session() as session:
        attachment = await attachment_data.get_report_attachment_by_id(session, attachment_id)
        if not attachment or attachment.report_id != report_id:
            raise HTTPException(status_code=404, detail="Вложение не найдено")

    abs_path = _abs_path(attachment.pdf_path)
    if not abs_path.is_file():
        raise HTTPException(
            status_code=410,
            detail="Файл вложения отсутствует на диске",
        )
    download_name = _attachment_filename(attachment.id, attachment.kind, attachment.title)
    return abs_path, download_name


# ========== СОЗДАНИЕ ==========

async def upload_attachment(
    *,
    report_id: int,
    kind: ReportAttachmentKind,
    title: Optional[str],
    files: List[UploadFile],
    current_user: User,
) -> dict:
    _check_permission(current_user, "report_modify", "загрузки вложений отчёта")

    # Сначала конвертируем файлы — это самая «дорогая» часть, нет смысла начинать
    # транзакцию БД, если конвертация упадёт.
    pdf_bytes, pages = await convert_uploads_to_pdf(files)
    size_bytes = len(pdf_bytes)

    async with new_session() as session:
        report = await report_data.get_report_by_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Отчёт с id {report_id} не найден")

        if report.user_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете добавлять вложения только в свои отчёты",
            )

        if report.status and report.status.name == 'Утверждён':
            raise HTTPException(
                status_code=400,
                detail="Отчёт утверждён — изменять вложения нельзя",
            )

        attachment = await attachment_data.create_report_attachment(
            session,
            report_id=report_id,
            kind=kind.value,
            title=(title or None),
            size_bytes=size_bytes,
            pages=pages,
            uploaded_by=current_user.id,
        )

        # Запись на диск. Если упадёт — БД-транзакция откатится автоматически.
        report_dir = _report_dir(report_id)
        report_dir.mkdir(parents=True, exist_ok=True)
        filename = _attachment_filename(attachment.id, kind.value, title)
        abs_path = report_dir / filename
        try:
            abs_path.write_bytes(pdf_bytes)
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Не удалось сохранить файл вложения: {exc}",
            )

        rel_path = str(Path("reports") / str(report_id) / filename).replace("\\", "/")
        await attachment_data.set_report_attachment_path(session, attachment.id, rel_path)
        await session.commit()

        # Перечитываем с загрузкой uploader для ответа.
        fresh = await attachment_data.get_report_attachment_by_id(session, attachment.id, load_uploader=True)
        return _to_response(fresh)


# ========== ЛИНКОВКА MOBILE-ФОТО (M5.3) ==========

async def link_mobile_photos(
    *,
    report_id: int,
    final_paths: List[str],
    title: Optional[str],
    kind: ReportAttachmentKind,
    current_user: User,
) -> dict:
    """Собрать mobile-загруженные фото (MEDIA/mobile/*.jpg) в один PDF-attachment.

    Работает без re-upload: фото уже на диске после chunked-upload (M1.5).
    Ограничение kind='report_photo' — фото с объекта, доказательство работ.
    """
    _check_permission(current_user, "report_modify", "линковки mobile-фото")

    # Валидация путей: они должны быть под MEDIA/mobile, без path-traversal.
    resolved_paths: List[Path] = []
    for rel in final_paths:
        if not rel or ".." in rel.split("/") or rel.startswith("/"):
            raise HTTPException(
                status_code=400,
                detail=f"Некорректный final_path: '{rel}'",
            )
        # M1.5 кладёт в MEDIA/mobile/<uuid>_<name>.jpg — принимаем как есть,
        # так и голое имя (для гибкости на случай если фронт отдал basename).
        candidate = MEDIA_PATH / rel
        candidate_alt = MEDIA_PATH / "mobile" / rel
        if candidate.is_file():
            resolved_paths.append(candidate)
        elif candidate_alt.is_file():
            resolved_paths.append(candidate_alt)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Файл '{rel}' не найден в MEDIA",
            )

    pdf_bytes, pages = await convert_disk_files_to_pdf(resolved_paths)
    size_bytes = len(pdf_bytes)

    async with new_session() as session:
        report = await report_data.get_report_by_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Отчёт с id {report_id} не найден")
        if report.user_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете добавлять вложения только в свои отчёты",
            )
        if report.status and report.status.name == 'Утверждён':
            raise HTTPException(
                status_code=400,
                detail="Отчёт утверждён — изменять вложения нельзя",
            )

        kind_str = kind.value
        attachment = await attachment_data.create_report_attachment(
            session,
            report_id=report_id,
            kind=kind_str,
            title=(title or None),
            size_bytes=size_bytes,
            pages=pages,
            uploaded_by=current_user.id,
        )

        report_dir = _report_dir(report_id)
        report_dir.mkdir(parents=True, exist_ok=True)
        filename = _attachment_filename(attachment.id, kind_str, title)
        abs_path = report_dir / filename
        try:
            abs_path.write_bytes(pdf_bytes)
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Не удалось сохранить файл вложения: {exc}",
            )

        rel_path = str(Path("reports") / str(report_id) / filename).replace("\\", "/")
        await attachment_data.set_report_attachment_path(session, attachment.id, rel_path)
        await session.commit()

        fresh = await attachment_data.get_report_attachment_by_id(
            session, attachment.id, load_uploader=True
        )
        return _to_response(fresh)


# ========== УДАЛЕНИЕ ==========

async def delete_attachment(
    report_id: int,
    attachment_id: int,
    current_user: User,
) -> bool:
    _check_permission(current_user, "report_modify", "удаления вложений отчёта")
    async with new_session() as session:
        attachment = await attachment_data.get_report_attachment_by_id(session, attachment_id)
        if not attachment or attachment.report_id != report_id:
            raise HTTPException(status_code=404, detail="Вложение не найдено")

        report = await report_data.get_report_by_id(session, report_id)
        if report and report.user_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете удалять вложения только в своих отчётах",
            )
        if report and report.status and report.status.name == 'Утверждён':  # spec_report_statuses после f3a4b5c6d7e8
            raise HTTPException(
                status_code=400,
                detail="Отчёт утверждён — изменять вложения нельзя",
            )

        rel_path = attachment.pdf_path
        await attachment_data.delete_report_attachment(session, attachment_id)
        await session.commit()

    # Файл с диска удаляем после коммита БД, чтобы при ошибке БД файл не пропал.
    if rel_path:
        try:
            _abs_path(rel_path).unlink(missing_ok=True)
        except OSError:
            pass
    return True


# ========== УБОРКА ПРИ УДАЛЕНИИ ОТЧЁТА ==========

def cleanup_report_directory(report_id: int) -> None:
    """Удалить папку media/reports/{report_id} целиком (вызывается из delete_report)."""
    shutil.rmtree(_report_dir(report_id), ignore_errors=True)
