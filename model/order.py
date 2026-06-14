# model/order.py
from typing import List, Optional, TYPE_CHECKING
from datetime import date

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


# модель заявки
class Order(Base):

    id: Mapped[int_pk]
    # Номер заявки. Для автогенерируемых формат:
    # "<object.number_in_contract>/<MM>/<YYYY>/<customer.short_name>/<contract.short_subject>/<seq>"
    # Длина под 200 — два текстовых куска (заказчик + предмет) могут быть длинными.
    number: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    spec_order_id: Mapped[int] = mapped_column(ForeignKey("spec_orders.id"), nullable=False)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    report_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    created_at: Mapped[date] = mapped_column(default=date.today)  # Добавил дату создания
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Добавил описание
    status: Mapped[str] = mapped_column(default="new")  # Добавил статус заявки
    # Начало периода обслуживания — заполняется только для авто-сгенерированных
    # «плановых» заявок. UNIQUE(object_id, spec_order_id, period_start_date)
    # WHERE period_start_date IS NOT NULL — защита от дублей при tick'ах.
    period_start_date: Mapped[Optional[date]] = mapped_column(nullable=True)

    # Все отношения через строки для избежания циклических импортов
    
    # Тип заявки (многие к одному)
    spec_order: Mapped["Spec_Order"] = relationship(
                                                        "Spec_Order",
                                                        back_populates="orders",  # Должно быть в Spec_Order
                                                        lazy="selectin"
                                                    )

    # Контракт (многие к одному)
    contract: Mapped["Contract"] = relationship(
                                                    "Contract",
                                                    back_populates="orders",  # Должно быть в Contract
                                                    lazy="selectin"
                                                )

    # Объект (многие к одному)
    object: Mapped["Object"] = relationship(
                                                "Object",
                                                back_populates="orders",  # Должно быть в Object
                                                lazy="selectin"
                                            )

    # Пользователь (многие к одному)
    user: Mapped["User"] = relationship(
        "User",
        back_populates="orders",  # Должно быть в User
        lazy="selectin"
    )
    
    # Отчёт (один к одному)
    report: Mapped[Optional["Report"]] = relationship(
        "Report",
        back_populates="order",  # Должно быть в Report
        lazy="selectin",
        uselist=False  # Важно для один-к-одному
    )

    def __str__(self):
        return f"Order(id={self.id}, number={self.number})"

    def __repr__(self):
        return str(self)