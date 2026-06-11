from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from database.database import (
    Base,
    int_pk,
    str_uniq,
    str_null_true,
)


# модель типа журнала (привязывается к объекту, рендерится по любому из объектов)
class Spec_Journal(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    short_name: Mapped[str_null_true]
    code: Mapped[Optional[str]] = mapped_column(unique=True, nullable=True)
    is_system: Mapped[bool] = mapped_column(default=False, server_default='false')
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    template_filename: Mapped[Optional[str]] = mapped_column(nullable=True)
    template_storage_path: Mapped[Optional[str]] = mapped_column(nullable=True)

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)
