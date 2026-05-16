from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Integer, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


# Связующая таблица operation <-> spec_equipment (M:M)
# Один тип оборудования имеет много операций, и одна операция
# может относиться к нескольким типам оборудования.
operations_spec_equipments = Table(
    "operations_spec_equipments",
    Base.metadata,
    Column("operation_id", Integer, ForeignKey("operations.id", ondelete="CASCADE"),
           primary_key=True),
    Column("spec_equipment_id", Integer, ForeignKey("spec_equipments.id", ondelete="CASCADE"),
           primary_key=True),
)


class Operation(Base):
    """
    Справочник операций для типов оборудования.

    Связь с Spec_Equipment — many-to-many через operations_spec_equipments.
    Поле description приходит автоматически из Base.
    """

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    short_name: Mapped[Optional[str]] = mapped_column(nullable=True)

    spec_equipments: Mapped[List["Spec_Equipment"]] = relationship(
        "Spec_Equipment",
        secondary=operations_spec_equipments,
        back_populates="operations",
        lazy="selectin",
    )

    def __str__(self):
        return f"Operation(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)
