from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class IssueAttachmentKind(str, Enum):
    photo = "photo"
    document = "document"
    other = "other"


class LinkIssueMobilePhotosRequest(BaseModel):
    """Тело запроса линковки фото из MEDIA/mobile/*.jpg к неисправности.

    Мобильный клиент грузит фото через chunked-upload (M1.5), получает
    final_path'ы и передаёт сюда — backend склеит их в один PDF.
    """
    final_paths: list[str] = Field(..., min_length=1, max_length=10)
    title: Optional[str] = Field(None, max_length=255)
    kind: IssueAttachmentKind = IssueAttachmentKind.photo


class IssueAttachmentResponse(BaseModel):
    """Информация о вложении неисправности (без пути на диске)."""
    id: int
    issue_id: int
    kind: IssueAttachmentKind
    title: Optional[str] = None
    size_bytes: int
    pages: int
    created_at: datetime = Field(..., description="Когда вложение было загружено")
    uploaded_by: int
    uploader_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
