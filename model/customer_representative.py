"""Представитель заказчика на объекте — подписывает выполнение работ узором.

Узор 4×4 задаёт сам представитель по одноразовой ссылке (своим телефоном,
исполнитель его не видит). Храним bcrypt-хеш, как у пароля. После
MAX_FAILED ошибок подряд — блокировка до новой ссылки. См.
service/customer_signature.py.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk

if TYPE_CHECKING:
    from model.object import Object


class Customer_Representative(Base):
    id: Mapped[int_pk]
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    position: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    pattern_hash: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    pattern_set_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Одноразовая ссылка на задание узора: в БД sha256 токена.
    enroll_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    enroll_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    object: Mapped["Object"] = relationship("Object", lazy="selectin")

    @property
    def has_pattern(self) -> bool:
        return bool(self.pattern_hash)

    @property
    def is_locked(self) -> bool:
        return self.locked_at is not None

    def __str__(self):
        return f"Customer_Representative(id={self.id}, {self.full_name})"
