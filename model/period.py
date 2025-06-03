from datetime import date
from typing import List

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
from model.object import Object


class Period(base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    period: Mapped[str_uniq]

    # с одним периоддом могут быть много объектов
    objects: Mapped[List[Object]] = relationship(Object,
                                                    back_populates="period")

    def __str__(self):
        return (f"{self.__class__.__name__}(id={self.id}, name={self.name}")

    def __repr__(self):
        return str(self)