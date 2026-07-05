from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING

from sqlalchemy import ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk

if TYPE_CHECKING:
    from model.user import User


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_jti: Mapped[str] = mapped_column(nullable=False, unique=True)
    device_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, default=None
    )
    user_agent: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    ip_address: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    geo_country: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    user: Mapped["User"] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"UserSession(id={self.id}, user_id={self.user_id}, jti={self.refresh_jti[:8]}...)"
