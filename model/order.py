from typing import List
from datetime import date

from sqlalchemy import ForeignKey, Text
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

from model.spec_order import Spec_Order


class Order(Base):

    id: Mapped[int_pk]
    number: Mapped[str]
    spec_order_id: Mapped[int] = mapped_column(ForeignKey("spec_orders.id"))    # тип заявки
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))        # контракт
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"))            # объект
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))                # пользователь, создавший заявку
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))            # отчёт

    # наименование типа заявки (один ко многим)
    spec_order: Mapped[Spec_Order] = relationship(Spec_Order,
                                                    back_populates="orders",
                                                    lazy="selectin")

    # отчёт по одному контракту может быть много заявок (один ко многим)
    contract: Mapped["Contract"] = relationship("Contract",
                                                back_populates="orders",
                                                lazy="selectin")

    # одна заявка может быть только на один объект (один ко многим)
    object_order: Mapped["Object"] = relationship("Object",
                                                back_populates="orders",
                                                lazy="selectin")

    # одну заявку может создать только один пользователь (один ко многим)
    user: Mapped["User"] = relationship("User",
                                        back_populates="orders",
                                        lazy="selectin")
    
    # одна заявка один отчёт(один к одному)
    report: Mapped["Report"] = relationship("Report",
                                            back_populates="order",
                                            lazy="selectin")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, number={self.number})"

    def __repr__(self):
        return str(self)