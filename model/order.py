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
    # Ответственный за исполнение (nullable — при создании может не быть
    # назначен, mobile "Мои" фильтрует по этому полю). Отдельно от user_id
    # (автор): один создал, другой ведёт. См. миграцию d1a2b3c4e5f6.
    assigned_to_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    report_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    created_at: Mapped[date] = mapped_column(default=date.today)  # Добавил дату создания
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Добавил описание
    # FK на справочник статусов заявок. Ранее было `status: Mapped[str]` без FK
    # (миграция f9a0b1c2d3e4). Ру-имя доступно через relationship —
    # spec_order_status.name; @property status/status_name ниже дают
    # API-совместимость (Response'ы по-прежнему возвращают string-код).
    status_id: Mapped[int] = mapped_column(
        ForeignKey("spec_order_statuses.id"), nullable=False
    )
    # Начало периода обслуживания — заполняется только для авто-сгенерированных
    # «плановых» заявок. UNIQUE(object_id, spec_order_id, period_start_date)
    # WHERE period_start_date IS NOT NULL — защита от дублей при tick'ах.
    period_start_date: Mapped[Optional[date]] = mapped_column(nullable=True)

    # Срок исполнения. Авто-заполняется по spec_order.sla_kind при create
    # (periodic → конец периода, from_creation → created_at + sla_days),
    # можно переопределить вручную в форме. NULL — «без срока» (маркер
    # температурной шкалы не показывается). Миграция f5c6d7e8f9a0.
    due_date: Mapped[Optional[date]] = mapped_column(nullable=True)

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

    # Пользователь (многие к одному). lazy="joined" — JOIN в основном
    # SELECT'е заявок вместо отдельного selectin'а; user обычно нужен
    # каждому order'у (автор) и не тащит вложенных коллекций.
    user: Mapped["User"] = relationship(
        "User",
        back_populates="orders",  # Должно быть в User
        lazy="joined",
        foreign_keys="Order.user_id",
    )

    # Ответственный (может отсутствовать). lazy="joined" — нужен рядом с
    # user (автор) в основном SELECT'е.
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="joined",
        foreign_keys="Order.assigned_to_id",
    )

    # Отчёт (один к одному)
    report: Mapped[Optional["Report"]] = relationship(
        "Report",
        back_populates="order",  # Должно быть в Report
        lazy="selectin",
        uselist=False  # Важно для один-к-одному
    )

    # Справочник статуса. lazy="joined" — читатели получают ру-имя без
    # отдельного SELECT'а.
    spec_order_status: Mapped["Spec_Order_Status"] = relationship(
        "Spec_Order_Status",
        lazy="joined",
    )

    def __str__(self):
        return f"Order(id={self.id}, number={self.number})"

    def __repr__(self):
        return str(self)