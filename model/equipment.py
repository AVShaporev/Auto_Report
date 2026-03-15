from typing import List, TYPE_CHECKING
from datetime import date

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq


class Equipment(Base):
    """
    Модель оборудования - упрощенная версия для первой итерации
    
    Связана с:
    - spec_equipment (тип оборудования)
    - objects_equipments (связка с объектами)
    """
    
    __tablename__ = "equipments"
    
    __table_args__ = (
        UniqueConstraint('inventory_number', name='uq_equipments_inventory_number'),
        UniqueConstraint('serial_number', name='uq_equipments_serial_number'),
    )

    id: Mapped[int_pk]
    name: Mapped[str_uniq] = mapped_column(
        comment="Наименование оборудования"
    )
    
    # Уникальные идентификаторы (обязательные)
    inventory_number: Mapped[str] = mapped_column(
        unique=True, 
        nullable=False, 
        comment="Инвентарный номер (уникальный)"
    )
    serial_number: Mapped[str] = mapped_column(
        unique=True, 
        nullable=False, 
        comment="Серийный (заводской) номер (уникальный)"
    )
    
    # Дата установки (обязательная)
    installation_date: Mapped[date] = mapped_column(
        nullable=False, 
        comment="Дата установки/ввода в эксплуатацию"
    )
    
    # Статус (упрощенный)
    is_active: Mapped[bool] = mapped_column(
        default=True,
        comment="Активно (true) / списано (false)"
    )
    
    # Внешние ключи
    spec_equipment_id: Mapped[int] = mapped_column(
        ForeignKey("spec_equipments.id"), 
        nullable=False,
        comment="ID типа оборудования"
    )

    # Отношения
    spec_equipment: Mapped["Spec_Equipment"] = relationship(
        "Spec_Equipment",
        back_populates="equipments",
        lazy="selectin"
    )

    # Связь с объектами через промежуточную таблицу
    objects_equipments: Mapped[List["Objects_Equipment"]] = relationship(
        "Objects_Equipment",
        back_populates="equipment",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"Equipment(id={self.id}, name={self.name}, inv={self.inventory_number})"

    def __repr__(self):
        return str(self)