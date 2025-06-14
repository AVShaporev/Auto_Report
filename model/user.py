from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true
from model.role import Role


class User(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    hash: Mapped[str]
    telegram_id: Mapped[str] = None
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))

    # Определяем отношения: один пользователь относится к одной роли
    # role: Mapped[Role] = relationship(Role,
    #                                     backref="role",
    #                                     uselist=False,
    #                                     foreign_keys=[role_id],
    #                                     lazy="joined"
    #                                     )
    role: Mapped[Role] = relationship(Role, back_populates="users")


    def __repr__(self):
        return (self.id, self.name)

    def __str__(self):
        return (self.id, self.name, self.role)