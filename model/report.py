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

from model.period import Period
# from model.contract import Contract
# from model.object import Object


class Report(Base):

    id: Mapped[int_pk]
    number: Mapped[str]
    check_pass: Mapped[bool]                                                    # флаг утверждения
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"))            # период обслуживания
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))        # контракт
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"))            # объект
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))            # пользователь, создавший отчёт

    # наименование периода обслуживания (один к одному)
    period: Mapped[Period] = relationship(Period,
                                            lazy="selectin")

    # отчёт по одному объекту может быть только один в одном контракте (многие к одному)
    contract: Mapped["Contract"] = relationship("Contract",
                                                back_populates="reports",
                                                lazy="selectin")

    # в одном отчете может быть только один объект (многие к одному)
    object_report: Mapped["Object"] = relationship("Object",
                                                back_populates="reports",
                                                lazy="selectin")

    # один отчет может создать только один пользователь
    user: Mapped["User"] = relationship("User",
                                        back_populates="reports",
                                        lazy="selectin")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, number={self.number})"

    def __repr__(self):
        return str(self)
        