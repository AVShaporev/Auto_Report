from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from core.dependencies import get_current_active_user
from model.user import User
from schema.report_attachment import (
    LinkMobilePhotosRequest,
    ReportAttachmentKind,
    ReportAttachmentResponse,
)
from service import report_attachment as attachment_service

router = APIRouter(prefix="/api/report", tags=["report-attachments"])


@router.get(
    "/{report_id}/attachments",
    response_model=List[ReportAttachmentResponse],
)
async def list_report_attachments(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить список вложений отчёта.

    Требуется право: report_read.
    """
    return await attachment_service.list_attachments(report_id, current_user)


@router.post(
    "/{report_id}/attachments",
    response_model=ReportAttachmentResponse,
)
async def upload_report_attachment(
    report_id: int,
    kind: ReportAttachmentKind = Form(..., description="Категория: act/journal/equipment/other"),
    title: Optional[str] = Form(None, description="Заголовок (необязательно)"),
    files: List[UploadFile] = File(..., description="Одно или несколько изображений или один PDF"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Загрузить вложение к отчёту.

    Несколько изображений склеиваются в один многостраничный PDF.
    Готовый PDF можно загрузить только один и без других файлов в том же запросе.

    Требуется право: report_modify. Утверждённый отчёт изменять нельзя.
    """
    return await attachment_service.upload_attachment(
        report_id=report_id,
        kind=kind,
        title=title,
        files=files,
        current_user=current_user,
    )


@router.post(
    "/{report_id}/attachments/link-mobile-photos",
    response_model=ReportAttachmentResponse,
)
async def link_mobile_photos(
    report_id: int,
    body: LinkMobilePhotosRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Прилинковать mobile-фото к отчёту (M5.3).

    Мобильный клиент сначала грузит фото через chunked-upload M1.5
    (POST /api/mobile/media/upload/init → PUT chunks → получает final_path),
    затем передаёт список final_path сюда. Backend собирает фото в один
    многостраничный PDF и создаёт Report_Attachment kind='report_photo'.

    Требуется право: report_modify. Утверждённый отчёт менять нельзя.
    """
    return await attachment_service.link_mobile_photos(
        report_id=report_id,
        final_paths=body.final_paths,
        title=body.title,
        kind=body.kind,
        current_user=current_user,
    )


@router.get("/{report_id}/attachments/{attachment_id}/file")
async def download_report_attachment(
    report_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Скачать PDF-файл вложения.

    Требуется право: report_read.
    """
    abs_path, filename = await attachment_service.get_attachment_for_download(
        report_id=report_id,
        attachment_id=attachment_id,
        current_user=current_user,
    )
    return FileResponse(
        path=str(abs_path),
        media_type="application/pdf",
        filename=filename,
    )


@router.delete("/{report_id}/attachments/{attachment_id}")
async def delete_report_attachment(
    report_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Удалить вложение отчёта.

    Требуется право: report_modify. Утверждённый отчёт изменять нельзя.
    """
    await attachment_service.delete_attachment(report_id, attachment_id, current_user)
    return {"status": "success", "message": "Вложение удалено"}
