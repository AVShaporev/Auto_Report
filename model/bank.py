from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import (
                            DeclarativeBase, 
                            Mapped, 
                            mapped_column, 
                            relationship
)

from database.database import (
                                Base, 
                                int_pk, 
                                str_uniq, 
                                str_null_true
)
# from model.organization import Organization

class Bank(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    bik: Mapped[str]
    inn: Mapped[str_uniq]

    # организациии для банка
    organizations: Mapped[List["Organization"]] = relationship("Organization",
                                                                back_populates="bank")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)