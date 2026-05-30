from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from core.dependencies import get_current_active_user
from model.user import User
from schema.issue_attachment import IssueAttachmentKind, IssueAttachmentResponse
from service import issue_attachment as attachment_service

router = APIRouter(prefix="/api/issue", tags=["issue-attachments"])


@router.get(
    "/{issue_id}/attachments",
    response_model=List[IssueAttachmentResponse],
)
async def list_issue_attachments(
    issue_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить список вложений неисправности.

    Требуется право: issue_read.
    """
    return await attachment_service.list_attachments(issue_id, current_user)


@router.post(
    "/{issue_id}/attachments",
    response_model=IssueAttachmentResponse,
)
async def upload_issue_attachment(
    issue_id: int,
    kind: IssueAttachmentKind = Form(..., description="Категория: photo/document/other"),
    title: Optional[str] = Form(None, description="Заголовок (необязательно)"),
    files: List[UploadFile] = File(..., description="Одно или несколько изображений или один PDF"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Загрузить вложение к неисправности.

    Несколько изображений склеиваются в один многостраничный PDF.
    Готовый PDF можно загрузить только один и без других файлов в том же запросе.

    Требуется право: issue_modify.
    """
    return await attachment_service.upload_attachment(
        issue_id=issue_id,
        kind=kind,
        title=title,
        files=files,
        current_user=current_user,
    )


@router.get("/{issue_id}/attachments/{attachment_id}/file")
async def download_issue_attachment(
    issue_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Скачать PDF-файл вложения.

    Требуется право: issue_read.
    """
    abs_path, filename = await attachment_service.get_attachment_for_download(
        issue_id=issue_id,
        attachment_id=attachment_id,
        current_user=current_user,
    )
    return FileResponse(
        path=str(abs_path),
        media_type="application/pdf",
        filename=filename,
    )


@router.delete("/{issue_id}/attachments/{attachment_id}")
async def delete_issue_attachment(
    issue_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Удалить вложение неисправности.

    Требуется право: issue_modify.
    """
    await attachment_service.delete_attachment(issue_id, attachment_id, current_user)
    return {"status": "success", "message": "Вложение удалено"}
