from typing import List, Optional
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

# модель типа заявки
class Spec_Order(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    short_name: Mapped[str_null_true]
    code: Mapped[Optional[str]] = mapped_column(unique=True, nullable=True)
    is_system: Mapped[bool] = mapped_column(default=False, server_default='false')
    # Флаги «вид заявки по умолчанию» для авто-генерации (один TRUE на флаг
    # на всю таблицу — гарантия partial UNIQUE-индексом в миграции).
    is_default_planned: Mapped[bool] = mapped_column(default=False, server_default='false')
    is_default_primary: Mapped[bool] = mapped_column(default=False, server_default='false')
    template_filename: Mapped[Optional[str]] = mapped_column(nullable=True)
    template_storage_path: Mapped[Optional[str]] = mapped_column(nullable=True)

    # SLA-режим — как считать due_date у заявок этого типа. Миграция
    # f5c6d7e8f9a0. CHECK-констрейнты sla_kind ∈ {periodic, from_creation,
    # manual} + sla_days обязателен ровно для 'from_creation'.
    #
    #   periodic       — до конца календарного периода объекта
    #                    (period_code monthly/quarterly/semiannual/yearly)
    #   from_creation  — created_at + sla_days (например АВР = 3 дня)
    #   manual         — юзер вводит due_date вручную в форме заявки
    sla_kind: Mapped[str] = mapped_column(
        default='manual', server_default='manual', nullable=False,
    )
    sla_days: Mapped[Optional[int]] = mapped_column(nullable=True)

    orders: Mapped[List["Order"]] = relationship(
                                                "Order",
                                                back_populates="spec_order"
                                                )

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)