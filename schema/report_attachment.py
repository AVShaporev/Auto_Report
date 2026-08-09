from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReportAttachmentKind(str, Enum):
    act = "act"
    journal = "journal"
    equipment = "equipment"
    other = "other"
    # Mobile-app линкует набор фото с объекта в одно вложение через
    # POST /api/report/{id}/attachments/link-mobile-photos (M5.3).
    report_photo = "report_photo"


class LinkMobilePhotosRequest(BaseModel):
    """Тело запроса линковки фото из MEDIA/mobile/*.jpg к отчёту.

    Мобильный клиент сначала грузит фото через chunked-upload (M1.5),
    получает final_path'ы, затем передаёт их сюда — backend соберёт
    все фото в один многостраничный PDF и создаст Report_Attachment.
    """
    final_paths: list[str] = Field(..., min_length=1, max_length=10)
    title: Optional[str] = Field(None, max_length=255)


class ReportAttachmentResponse(BaseModel):
    """Информация о вложении отчёта (без пути на диске)."""
    id: int
    report_id: int
    kind: ReportAttachmentKind
    title: Optional[str] = None
    size_bytes: int
    pages: int
    created_at: datetime = Field(..., description="Когда вложение было загружено")
    uploaded_by: int
    uploader_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
