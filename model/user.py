from typing import List

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true
from model.role import Role
from model.report import Report


class User(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    hash: Mapped[str]
    telegram_id: Mapped[str] = None
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))

    # Определяем отношения: один пользователь относится к одной роли
    role: Mapped[Role] = relationship(Role, back_populates="users")

    # отчеты пользователя (один пользователь - много отчетов)
    reports: Mapped[List[Report]] = relationship(Report,
                                                    back_populates="user",
                                                    lazy="selectin")


    def __repr__(self):
        return (self.id, self.name)

    def __str__(self):
        return (self.id, self.name, self.role)