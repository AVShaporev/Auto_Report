from typing import List, Optional, TYPE_CHECKING
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
    
    # Статус (справочник spec_statuss) и приоритет (справочник spec_prioritys)
    status_id: Mapped[int] = mapped_column(
        ForeignKey("spec_statuss.id"),
        nullable=False,
        comment="ID статуса из справочника spec_statuss"
    )
    priority_id: Mapped[int] = mapped_column(
        ForeignKey("spec_prioritys.id"),
        nullable=False,
        comment="ID приоритета из справочника spec_prioritys"
    )
    
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
    status: Mapped["Spec_Status"] = relationship(
        "Spec_Status",
        back_populates="issues",
        lazy="selectin"
    )

    priority: Mapped["Spec_Priority"] = relationship(
        "Spec_Priority",
        back_populates="issues",
        lazy="selectin"
    )

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

    attachments: Mapped[List["Issue_Attachment"]] = relationship(
        "Issue_Attachment",
        back_populates="issue",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __str__(self):
        return f"Issue(id={self.id}, number={self.number}, title={self.title})"

    def __repr__(self):
        return str(self)