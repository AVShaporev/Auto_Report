from typing import List
from datetime import date

from sqlalchemy import (
                        ForeignKey,
                        text, 
                        Text
)
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
# from model.object import Object
from model.equipment import Equipment

class Objects_Equipment(Base):

    id: Mapped[int_pk]
    count: Mapped[int]
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"),
                                            nullable=False)     # объект
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipments.id"),
                                                nullable=False) # наименование оборудования
    
    # наименование объекта
    objects: Mapped["Object"] = relationship("Object",
                                            back_populates="objects_equipments")
    
    # наименование оборудования
    equipments: Mapped[Equipment] = relationship(Equipment,
                                                    back_populates="objects_equipment")
    
    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)
