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
# from model.organization import Organization
# from model.spec_contract import Spec_Contract
# from model.contract import Contract
# from model.object import Object


class Sub_Contract(Base):

    id: Mapped[int_pk]
    number: Mapped[str]
    date_of_consclusion: Mapped[date]
    subject: Mapped[str]
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id")) # id контракта

    # одно доп.соглашение - один контракт
    contract_subject: Mapped["Contract"] = relationship("Contract",
                                                            back_populates = "sub_contract_subjects")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.number})"

    def __repr__(self):
        return str(self)
