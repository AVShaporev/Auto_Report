from typing import List, TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true

# Используем TYPE_CHECKING для подсказок типов без реального импорта
if TYPE_CHECKING:
    from model.role import Role
    from model.report import Report
    from model.order import Order

class User(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    full_name: Mapped[str] = None
    hash: Mapped[str]
    email: Mapped[str] = None
    phone: Mapped[str] = None
    telegram_id: Mapped[str] = None
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(default=True)

    # Отношения с использованием строк вместо прямых импортов
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="users",
        lazy="selectin"
    )

    reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="user",
        lazy="selectin"
    )

    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="user",
        lazy="selectin"
    )

    def __repr__(self):
        return f"User(id={self.id}, name={self.name})"

    def __str__(self):
        return f"User(id={self.id}, name={self.name})"