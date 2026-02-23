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


class Spec_Equipment(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]

    equipments: Mapped[List["Equipment"]] = relationship("Equipment",
                                                            back_populates="spec_equipment",
                                                            lazy="selectin"
                                                            )
    
    def __str__(self):
        return (f"{self.__class__.__name__}(id={self.id}, name={self.name}")

    def __repr__(self):
        return f"Spec_Equipment(id={self.id}, name={self.name})"