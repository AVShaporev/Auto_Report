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

# модель типа оборудования
class Spec_Equipment(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    is_system: Mapped[bool] = mapped_column(default=False, server_default='false')

    # lazy="select" (default) — backref'ы не грузим автоматически.
    # data/spec_equipment.py явно подгружает .equipments через
    # selectinload(Spec_Equipment.equipments) когда нужно (load_equipments=True).
    # .operations подгружается в data/equipment.py для equipment-detail-view
    # как chain: selectinload(Equipment.spec_equipment).selectinload(Spec_Equipment.operations).
    equipments: Mapped[List["Equipment"]] = relationship("Equipment",
                                                            back_populates="spec_equipment",
                                                            )

    # M:M с операциями (operations_spec_equipments) — определена в model/operation.py
    operations: Mapped[List["Operation"]] = relationship(
        "Operation",
        secondary="operations_spec_equipments",
        back_populates="spec_equipments",
    )

    def __str__(self):
        return (f"{self.__class__.__name__}(id={self.id}, name={self.name}")

    def __repr__(self):
        return f"Spec_Equipment(id={self.id}, name={self.name})"