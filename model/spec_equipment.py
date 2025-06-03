from datetime import date

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import (
                            DeclarativeBase, 
                            Mapped, 
                            mapped_column, 
                            relationship
)
from model.equipment import Equipment


class Spec_Equipment(Base):

    id: Mapped[int]
    name: Mapped[str_uniq]

    equipments: Mapped[List[Equipment]] = relationship(Equipment,
                                                        back_populates="spec_equipment")
    
    def __str__(self):
        return (f"{self.__class__.__name__}(id={self.id}, name={self.name}")

    def __repr__(self):
        return str(self)