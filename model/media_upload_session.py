from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base, int_pk


class MediaUploadSession(Base):
    __tablename__ = "media_upload_sessions"

    id: Mapped[int_pk]
    upload_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    user_name: Mapped[str] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(nullable=False)
    filename: Mapped[str] = mapped_column(nullable=False)
    total_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    tmp_path: Mapped[str] = mapped_column(nullable=False)
    final_path: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    is_complete: Mapped[bool] = mapped_column(default=False, server_default="false")
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"MediaUploadSession(upload_id={self.upload_id[:8]}..., "
            f"kind={self.kind}, {self.received_bytes}/{self.total_size})"
        )
