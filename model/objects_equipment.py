from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk

if TYPE_CHECKING:
    from model.object import Object
    from model.equipment import Equipment
    from model.issue import Issue

class Objects_Equipment(Base):
    """
    Связующая модель для оборудования на объектах
    
    Позволяет учитывать количество единиц оборудования на каждом объекте
    """
    
    __table_args__ = (
        UniqueConstraint('object_id', 'equipment_id', name='uq_object_equipment'),
    )

    id: Mapped[int_pk]
    count: Mapped[int] = mapped_column(nullable=False, default=1, comment="Количество единиц оборудования на объекте")
    
    # Внешние ключи
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

    # Отношения
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
    
    # 👇 НОВОЕ: неисправности для этого конкретного оборудования на объекте
    issues: Mapped[List["Issue"]] = relationship(
                                                    "Issue",
                                                    back_populates="object_equipment",
                                                    lazy="selectin",
                                                    cascade="all, delete-orphan"  # При удалении связи удаляются и связанные неисправности
                                                )

    def __str__(self):
        return f"Objects_Equipment(id={self.id}, object_id={self.object_id}, equipment_id={self.equipment_id}, count={self.count})"

    def __repr__(self):
        return str(self)