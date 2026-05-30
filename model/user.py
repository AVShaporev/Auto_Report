from typing import List, TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


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
    # role: joined — нужна на КАЖДЫЙ authed request для проверки прав;
    # joined даёт LEFT OUTER JOIN в одном SELECT, без отдельного round-trip.
    role: Mapped["Role"] = relationship(
                                        "Role",
                                        back_populates="users",
                                        lazy="joined"
                                        )

    # Коллекции: lazy="select" (default) — НЕ грузим автоматически.
    # Никто из текущего кода эти связи не читает; data-слой может опт-инить через selectinload().
    reports: Mapped[List["Report"]] = relationship(
                                                    "Report",
                                                    back_populates="user"
                                                    )

    orders: Mapped[List["Order"]] = relationship(
                                                "Order",
                                                back_populates="user"
                                                )

    reported_issues: Mapped[List["Issue"]] = relationship(
                                                        "Issue",
                                                        foreign_keys="Issue.reported_by_id",
                                                        back_populates="reported_by"
                                                        )

    assigned_issues: Mapped[List["Issue"]] = relationship(
                                                        "Issue",
                                                        foreign_keys="Issue.assigned_to_id",
                                                        back_populates="assigned_to"
                                                        )

    def __repr__(self):
        return f"User(id={self.id}, name={self.name})"

    def __str__(self):
        return f"User(id={self.id}, name={self.name})"