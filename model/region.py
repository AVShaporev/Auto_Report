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
from model.spec_region import Spec_Region
# from model.organization import Organization
from model.object import Object

class Region(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    symbol: Mapped[str_uniq]
    spec_region_id: Mapped[Spec_Region] = mapped_column(ForeignKey("spec_regions.id")) # тип региона

    # у одного региона может быть только один тип
    spec_region: Mapped[Spec_Region] = relationship(Spec_Region,
                                                        back_populates="regions",
                                                        lazy="selectin")
    
    # в одном регионе может быть много организаций
    organizations: Mapped[List["Organization"]] = relationship("Organization",
                                                                back_populates="region")

    # в одном регионе может быть много организаций
    objects: Mapped[List[Object]] = relationship(Object,
                                                    back_populates="region")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)