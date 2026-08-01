from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk

if TYPE_CHECKING:
    from model.user import User


class PushToken(Base):
    __tablename__ = "push_tokens"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(nullable=False)
    token: Mapped[str] = mapped_column(nullable=False, unique=True)
    device_id: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    app_version: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")

    user: Mapped["User"] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"PushToken(id={self.id}, user_id={self.user_id}, platform={self.platform})"
