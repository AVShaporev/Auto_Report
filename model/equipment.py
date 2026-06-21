from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq


class Equipment(Base):
    """
    Модель оборудования (справочник)

    Связана с:
    - spec_equipment (тип оборудования)
    - spec_system  (тип обслуживаемой системы — опционально, как «по умолчанию»;
      на конкретном объекте может быть переопределено в Objects_Equipment)
    - objects_equipments (связка с объектами; инв./серийный номер и дата установки
      хранятся именно там, поскольку относятся к конкретному экземпляру на объекте)
    """

    __tablename__ = "equipments"

    id: Mapped[int_pk]
    name: Mapped[str_uniq] = mapped_column(
        comment="Наименование оборудования"
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        comment="Активно (true) / списано (false)"
    )

    spec_equipment_id: Mapped[int] = mapped_column(
        ForeignKey("spec_equipments.id"),
        nullable=False,
        comment="ID типа оборудования"
    )

    spec_system_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("spec_systems.id"),
        nullable=True,
        comment="ID типа обслуживаемой системы по умолчанию (опционально)",
    )

    spec_equipment: Mapped["Spec_Equipment"] = relationship(
        "Spec_Equipment",
        back_populates="equipments",
        lazy="selectin"
    )

    spec_system: Mapped[Optional["Spec_System"]] = relationship(
        "Spec_System",
        lazy="selectin",
    )

    # lazy="select" (default) — data/equipment.py явно подгружает через
    # selectinload(Equipment.objects_equipments) при load_relations=True
    # (для delete-guard в service/equipment.py:287).
    objects_equipments: Mapped[List["Objects_Equipment"]] = relationship(
        "Objects_Equipment",
        back_populates="equipment",
        cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"Equipment(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)
