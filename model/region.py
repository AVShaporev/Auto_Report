# model/region.py
from typing import List, TYPE_CHECKING
from datetime import date

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


class Region(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    symbol: Mapped[str_uniq]
    spec_region_id: Mapped[int] = mapped_column(
                                                ForeignKey("spec_regions.id")
                                                )

    # Все отношения через строки
    spec_region: Mapped["Spec_Region"] = relationship(
                                                        "Spec_Region",
                                                        back_populates="regions",
                                                        lazy="selectin"
                                                    )
    
    organizations: Mapped[List["Organization"]] = relationship(
                                                                    "Organization",
                                                                    back_populates="region"
                                                                )

    objects: Mapped[List["Object"]] = relationship(
                                                    "Object",
                                                    back_populates="region"
                                                    )

    def __str__(self):
        return f"Region(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)