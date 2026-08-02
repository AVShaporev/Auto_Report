from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, LargeBinary, SmallInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base, int_pk


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[int_pk]
    user_name: Mapped[str] = mapped_column(nullable=False)
    key: Mapped[str] = mapped_column(nullable=False)
    method: Mapped[str] = mapped_column(nullable=False)
    path: Mapped[str] = mapped_column(nullable=False)
    status_code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    response_body: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    response_headers: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=None
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"IdempotencyKey(user={self.user_name}, key={self.key[:8]}..., "
            f"{self.method} {self.path} → {self.status_code})"
        )
