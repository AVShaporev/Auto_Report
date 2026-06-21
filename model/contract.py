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


# модель контракта
class Contract(Base):

    id: Mapped[int_pk]
    number: Mapped[str]
    date_of_consclusion: Mapped[date]
    date_of_completion: Mapped[date]
    summ: Mapped[float]
    subject: Mapped[str]
    short_subject: Mapped[str]
    type_contract: Mapped[str]
    spec_contract_id: Mapped[int] = mapped_column(ForeignKey("spec_contracts.id"))   # тип контракта
    customer_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))        # заказчик
    executor_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))        # подрядчик

    # Тип контракта (один контракт - один тип контракта)
    spec_contract: Mapped["Spec_Contract"] = relationship(
                                                            "Spec_Contract",
                                                            back_populates="contracts",  # Должно совпадать с Spec_Contract.contracts
                                                            lazy="selectin"
                                                        )

    # Заказчик (один контракт - один заказчик)
    customer: Mapped["Organization"] = relationship("Organization",
                                                        backref="customer_name",
                                                        uselist=False,
                                                        foreign_keys=[customer_id],
                                                        lazy="joined")

    # Подрядчик (один контракт - один подрядчик)
    executor: Mapped["Organization"] = relationship("Organization",
                                                        backref="executor_name",
                                                        uselist=False,
                                                        foreign_keys=[executor_id],
                                                        lazy="joined")

    # дополнительные соглашения (один контракт - ноль или много доп.соглашений)
    sub_contract_subjects: Mapped[List["Sub_Contract"]] = relationship(
        "Sub_Contract", 
        back_populates="contract_subject")


    # объекты (один контракт - один или много объектов)
    objects: Mapped[List["Object"]] = relationship("Object", 
                                                    back_populates="contract",
                                                    lazy="subquery")

    # отчеты по объекту (один контракт - много отчетов)
    # lazy="select" (default) — data/contract.py подгружает явно через
    # selectinload(Contract.reports/orders) когда нужно (load_relations=True
    # в get_contract_by_id для delete-guard); list-эндпоинты используют
    # raiseload, чтобы случайное обращение упало громко, а не молча тащило
    # каскад.
    reports: Mapped[List["Report"]] = relationship(
                                                        "Report",
                                                        back_populates="contract",  # Должно совпадать с Report.contract
                                                    )

    # заявки по объекту (один контракт - много заявок)
    orders: Mapped[List["Order"]] = relationship("Order",
                                                back_populates="contract",
                                                )

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, number={self.number})"

    def __repr__(self):
        return str(self)

    