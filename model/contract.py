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
from model.organization import Organization
from model.spec_contract import Spec_Contract
from model.sub_contract import Sub_Contract
from model.object import Object


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
    exeсutor_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))        # подрядчик

    # Тип контракта (один контракт - один тип контракта)
    spec_contract: Mapped[Spec_Contract] = relationship(Spec_Contract, back_populates="contracts")

    # Заказчик (один контракт - один заказчик)
    customer: Mapped[Organization] = relationship(Organization, back_populates="customers")

    # Подрядчик (один контракт - один подрядчик)
    exeсutor: Mapped[Organization] = relationship(Organization, back_populates="exeсutors")

    # дополнительные соглашения (один контракт - ноль или много доп.соглашений)
    sub_contract_subjects: Mapped[List[Sub_Contract]] = relationship(
        Sub_Contract, 
        back_populates="contract_subject")


    # объекты (один контракт - один или много объектов)
    objects: Mapped[List[Object]] = relationship(
        Object, 
        back_populates="object")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.number})"

    def __repr__(self):
        return str(self)

    