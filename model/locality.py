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


# модель типа населенного пункта
class Locality(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    spec_locality_id: Mapped[int] = mapped_column(ForeignKey("spec_localitys.id"), nullable=True)

    # один населенный пункт - один тип населенного пункта
    spec_locality: Mapped["Spec_Locality"] = relationship("Spec_Locality")

    # в одном насленном пункте может быть несколько организаций
    organizations: Mapped[List["Organization"]] = relationship("Organization",
                                                                back_populates="locality")

    # в одном насленном пункте может быть несколько объектов
    objects: Mapped[List["Object"]] = relationship(
                                                    "Object",
                                                    back_populates="locality"
                                                    )

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)