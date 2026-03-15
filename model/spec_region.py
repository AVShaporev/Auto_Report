# model/spec_region.py
from typing import List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship
from database.database import Base, int_pk, str_uniq


class Spec_Region(Base):
    
    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    
    regions: Mapped[List["Region"]] = relationship(
                                                        "Region",
                                                        back_populates="spec_region",
                                                        lazy="selectin"
                                                    )
    
    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)