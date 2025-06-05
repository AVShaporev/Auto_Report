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
# from model.organization import Organization


class Spec_Build(Base):

    id: Mapped[int_pk]
    name:Mapped[str_uniq]

    # в одном типе строения может находится несколько организаций
    organizations: Mapped[List["Organization"]] = relationship("Organization",
                                                                back_populates="spec_build")

    def __str__(self):
        return (f"{self.__class__.__name__}(id={self.id}, name={self.name}")

    def __repr__(self):
        return str(self)