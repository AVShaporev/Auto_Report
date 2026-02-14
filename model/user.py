from typing import List

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true
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

    # Определяем отношения: один пользователь относится к одной роли
    role: Mapped[Role] = relationship(Role, 
                                        back_populates="users",
                                        lazy="selectin")

    # отчеты пользователя (один пользователь - много отчетов)
    reports: Mapped[List[Report]] = relationship(Report,
                                                    back_populates="user",
                                                    lazy="selectin")

    # заявки пользователя (один пользователь - много заявок)
    orders: Mapped[List[Order]] = relationship(Order,
                                                    back_populates="user",
                                                    lazy="selectin")


    def __repr__(self):
        return (self.id, self.name)

    def __str__(self):
        return (self.id, self.name, self.role)