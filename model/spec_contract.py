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
from model.contract import Contract


class Spec_Contract(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]

    # у одного типа контракта может быть много контрактов
    contracts: Mapped[List[Contract]] = relationship(
                                                    Contract,
                                                    back_populates="spec_contract")
    
    def __str__(self):
        return (f"{self.__class__.__name__}(id={self.id}, name={self.name}")

    def __repr__(self):
        return str(self)