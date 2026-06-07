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

# модель типа строения
class Spec_Build(Base):

    id: Mapped[int_pk]
    name:Mapped[str_uniq]
    is_system: Mapped[bool] = mapped_column(default=False, server_default='false')

    # в одном типе строения может находится несколько организаций
    organizations: Mapped[List["Organization"]] = relationship(
                                                                "Organization",
                                                                back_populates="spec_build"
                                                                )

    # в одном типе строения может находится несколько объектов
    objects: Mapped[List["Object"]] = relationship(
                                                        "Object",
                                                        back_populates="spec_build"
                                                    )

    def __str__(self):
        return (f"{self.__class__.__name__}(id={self.id}, name={self.name}")

    def __repr__(self):
        return str(self)