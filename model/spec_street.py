from typing import List
from datetime import date

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
# from model.street import Street

# модель типа улицы
class Spec_Street(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    short_name: Mapped[str]

    # к одному типу улицы может относится несколько улиц
    streets: Mapped[List["Street"]] = relationship(
                                                    "Street",
                                                    back_populates="spec_street"
                                                    )

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)