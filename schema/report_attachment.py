from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReportAttachmentKind(str, Enum):
    act = "act"
    journal = "journal"
    equipment = "equipment"
    other = "other"


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
