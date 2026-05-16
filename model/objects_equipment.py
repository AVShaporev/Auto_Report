from typing import Optional, List, TYPE_CHECKING
from datetime import date

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk

if TYPE_CHECKING:
    from model.object import Object
    from model.equipment import Equipment
    from model.issue import Issue
    from model.spec_system import Spec_System


class Objects_Equipment(Base):
    """
    Связующая модель оборудования на объектах.

    Учитывает количество единиц оборудования на конкретном объекте, а также
    параметры конкретного экземпляра: инвентарный номер, серийный (заводской)
    номер и дату установки. Все три параметра — необязательные и без уникальности.
    """

    __table_args__ = (
        UniqueConstraint('object_id', 'equipment_id', name='uq_object_equipment'),
    )

    id: Mapped[int_pk]
    count: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        comment="Количество единиц оборудования на объекте"
    )

    inventory_number: Mapped[Optional[str]] = mapped_column(
        nullable=True,
        comment="Инвентарный номер экземпляра на объекте"
    )
    serial_number: Mapped[Optional[str]] = mapped_column(
        nullable=True,
        comment="Серийный (заводской) номер экземпляра на объекте"
    )
    installation_date: Mapped[Optional[date]] = mapped_column(
        nullable=True,
        comment="Дата установки/ввода в эксплуатацию"
    )

    object_id: Mapped[int] = mapped_column(
        ForeignKey("objects.id"),
        nullable=False,
        comment="ID объекта"
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipments.id"),
        nullable=False,
        comment="ID оборудования"
    )
    spec_system_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("spec_systems.id"),
        nullable=True,
        comment="ID типа обслуживаемой системы (опционально)",
    )

    object: Mapped["Object"] = relationship(
        "Object",
        back_populates="objects_equipments",
        lazy="selectin"
    )

    equipment: Mapped["Equipment"] = relationship(
        "Equipment",
        back_populates="objects_equipments",
        lazy="selectin"
    )

    spec_system: Mapped[Optional["Spec_System"]] = relationship(
        "Spec_System",
        back_populates="objects_equipments",
        lazy="selectin",
    )

    issues: Mapped[List["Issue"]] = relationship(
        "Issue",
        back_populates="object_equipment",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __str__(self):
        return (
            f"Objects_Equipment(id={self.id}, object_id={self.object_id}, "
            f"equipment_id={self.equipment_id}, count={self.count})"
        )

    def __repr__(self):
        return str(self)
