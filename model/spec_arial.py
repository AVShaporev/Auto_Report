from typing import List, TYPE_CHECKING
from datetime import date

from sqlalchemy import (ForeignKey,
                        text, 
                        Text)
from sqlalchemy.orm import (DeclarativeBase, 
                            Mapped, 
                            mapped_column, 
                            relationship)

from database.database import (Base, 
                                int_pk, 
                                str_uniq, 
                                str_null_true)


# модель типа районов
class Spec_Arial(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]

    # Отношение: один тип района может включать несколько наименований районов
    arials: Mapped[List["Arial"]] = relationship("Arial",
                                                    back_populates="spec_arial")

    def __str__(self):
        return (f"{self.__class__.__name__}(id={self.id}, name={self.name}")

    def __repr__(self):
        return str(self)