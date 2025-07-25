from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import (DeclarativeBase, 
                            Mapped, 
                            mapped_column, 
                            relationship)

from database.database import (Base, 
                                int_pk, 
                                str_uniq, 
                                str_null_true)


from model.spec_arial import Spec_Arial



# модель района
class Arial(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    spec_arial_id: Mapped[int] = mapped_column(ForeignKey("spec_arials.id"))

    # название типа района
    spec_arial: Mapped["Spec_Arial"] = relationship("Spec_Arial",
                                                        back_populates="arials",
                                                        lazy="selectin")

    # в одном районе может находиться несколько организаций
    organizations: Mapped[List["Organization"]] = relationship("Organization",
                                                                back_populates="arial")


    # в одном районе может находиться несколько объектов
    objects: Mapped[List["Object"]] = relationship("Object",
                                                    back_populates="arial")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)

    