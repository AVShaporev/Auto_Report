from typing import List
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
# from model.locality import Locality


class Spec_Locality(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    short_name: Mapped[str_null_true]
    
    localitys: Mapped[List["Locality"]] = relationship("Locality",
                                                        back_populates="spec_locality")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)