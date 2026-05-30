from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class IssueAttachmentKind(str, Enum):
    photo = "photo"
    document = "document"
    other = "other"


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
