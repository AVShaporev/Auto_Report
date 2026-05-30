"""
Бизнес-логика работы с вложениями неисправности (PDF, сконвертированные из фото).
"""
import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile

from config import MEDIA_PATH
from data import issue as issue_data
from data import issue_attachment as attachment_data
from database.database import new_session
from model.issue_attachment import Issue_Attachment
from model.user import User
from schema.issue_attachment import IssueAttachmentKind
from service.attachment_converter import convert_uploads_to_pdf


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
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return cleaned[:60] or fallback


def _attachment_filename(attachment_id: int, kind: str, title: Optional[str]) -> str:
    slug = _slugify(title or "", fallback=kind)
    return f"{attachment_id}_{slug}.pdf"


def _issue_dir(issue_id: int) -> Path:
    return MEDIA_PATH / "issues" / str(issue_id)


def _abs_path(rel_path: str) -> Path:
    return MEDIA_PATH / rel_path


def _to_response(att: Issue_Attachment) -> dict:
    return {
        "id": att.id,
        "issue_id": att.issue_id,
        "kind": att.kind,
        "title": att.title,
        "size_bytes": att.size_bytes,
        "pages": att.pages,
        "created_at": att.created_at,
        "uploaded_by": att.uploaded_by,
        "uploader_name": att.uploader.name if att.uploader else None,
    }


# ========== ПОЛУЧЕНИЕ ==========

async def list_attachments(issue_id: int, current_user: User) -> List[dict]:
    _check_permission(current_user, "issue_read", "просмотра вложений неисправности")
    async with new_session() as session:
        issue = await issue_data.get_issue_by_id(session, issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail=f"Неисправность с id {issue_id} не найдена")
        items = await attachment_data.get_issue_attachment_by_issue(session, issue_id)
        return [_to_response(item) for item in items]


async def get_attachment_for_download(
    issue_id: int,
    attachment_id: int,
    current_user: User,
) -> Tuple[Path, str]:
    """Вернуть (абсолютный_путь_к_файлу, имя_для_отдачи)."""
    _check_permission(current_user, "issue_read", "скачивания вложений неисправности")
    async with new_session() as session:
        attachment = await attachment_data.get_issue_attachment_by_id(session, attachment_id)
        if not attachment or attachment.issue_id != issue_id:
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
    issue_id: int,
    kind: IssueAttachmentKind,
    title: Optional[str],
    files: List[UploadFile],
    current_user: User,
) -> dict:
    _check_permission(current_user, "issue_modify", "загрузки вложений неисправности")

    # Сначала конвертируем файлы — это самая «дорогая» часть, нет смысла начинать
    # транзакцию БД, если конвертация упадёт.
    pdf_bytes, pages = await convert_uploads_to_pdf(files)
    size_bytes = len(pdf_bytes)

    async with new_session() as session:
        issue = await issue_data.get_issue_by_id(session, issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail=f"Неисправность с id {issue_id} не найдена")

        if issue.reported_by_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете добавлять вложения только к своим неисправностям",
            )

        attachment = await attachment_data.create_issue_attachment(
            session,
            issue_id=issue_id,
            kind=kind.value,
            title=(title or None),
            size_bytes=size_bytes,
            pages=pages,
            uploaded_by=current_user.id,
        )

        # Запись на диск. Если упадёт — БД-транзакция откатится автоматически.
        issue_dir = _issue_dir(issue_id)
        issue_dir.mkdir(parents=True, exist_ok=True)
        filename = _attachment_filename(attachment.id, kind.value, title)
        abs_path = issue_dir / filename
        try:
            abs_path.write_bytes(pdf_bytes)
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Не удалось сохранить файл вложения: {exc}",
            )

        rel_path = str(Path("issues") / str(issue_id) / filename).replace("\\", "/")
        await attachment_data.set_issue_attachment_path(session, attachment.id, rel_path)
        await session.commit()

        # Перечитываем с загрузкой uploader для ответа.
        fresh = await attachment_data.get_issue_attachment_by_id(session, attachment.id, load_uploader=True)
        return _to_response(fresh)


# ========== УДАЛЕНИЕ ==========

async def delete_attachment(
    issue_id: int,
    attachment_id: int,
    current_user: User,
) -> bool:
    _check_permission(current_user, "issue_modify", "удаления вложений неисправности")
    async with new_session() as session:
        attachment = await attachment_data.get_issue_attachment_by_id(session, attachment_id)
        if not attachment or attachment.issue_id != issue_id:
            raise HTTPException(status_code=404, detail="Вложение не найдено")

        issue = await issue_data.get_issue_by_id(session, issue_id)
        if issue and issue.reported_by_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете удалять вложения только к своим неисправностям",
            )

        rel_path = attachment.pdf_path
        await attachment_data.delete_issue_attachment(session, attachment_id)
        await session.commit()

    # Файл с диска удаляем после коммита БД, чтобы при ошибке БД файл не пропал.
    if rel_path:
        try:
            _abs_path(rel_path).unlink(missing_ok=True)
        except OSError:
            pass
    return True


# ========== УБОРКА ПРИ УДАЛЕНИИ НЕИСПРАВНОСТИ ==========

def cleanup_issue_directory(issue_id: int) -> None:
    """Удалить папку media/issues/{issue_id} целиком (вызывается из delete_issue)."""
    shutil.rmtree(_issue_dir(issue_id), ignore_errors=True)
