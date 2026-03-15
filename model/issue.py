from typing import Optional, TYPE_CHECKING
from datetime import date, datetime
from sqlalchemy import ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk


class Issue(Base):
    """
    Модель неисправности
    
    Связана с конкретным оборудованием на конкретном объекте через objects_equipment
    """

    id: Mapped[int_pk]
    
    # Основная информация
    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="Номер неисправности")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="Краткое описание")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Подробное описание")
    
    # Статус и приоритет
    status: Mapped[str] = mapped_column(String(20), default="new", comment="Статус: new, in_progress, resolved, closed")
    priority: Mapped[str] = mapped_column(String(20), default="medium", comment="Приоритет: low, medium, high, critical")
    
    # Даты
    detected_date: Mapped[date] = mapped_column(nullable=False, comment="Дата обнаружения")
    resolved_date: Mapped[Optional[date]] = mapped_column(nullable=True, comment="Дата устранения")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, comment="Дата создания записи")
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=datetime.utcnow, comment="Дата обновления")
    
    # Флаги
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, comment="Признак устранения")
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, comment="Критическая неисправность")
    
    # 👇 ИЗМЕНЕНО: теперь ссылаемся на objects_equipment вместо прямых связей
    object_equipment_id: Mapped[int] = mapped_column(
        ForeignKey("objects_equipments.id"), 
        nullable=False, 
        comment="ID связи объекта с оборудованием"
    )
    
    reported_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), 
        nullable=False, 
        comment="ID пользователя, сообщившего о неисправности"
    )
    
    assigned_to_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), 
        nullable=True, 
        comment="ID ответственного пользователя"
    )

    # 👇 ИЗМЕНЕНО: отношения
    object_equipment: Mapped["Objects_Equipment"] = relationship(
        "Objects_Equipment",
        back_populates="issues",
        lazy="selectin"
    )
    
    reported_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[reported_by_id],
        back_populates="reported_issues",
        lazy="selectin"
    )
    
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_issues",
        lazy="selectin"
    )

    def __str__(self):
        return f"Issue(id={self.id}, number={self.number}, title={self.title})"

    def __repr__(self):
        return str(self)