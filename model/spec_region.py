# model/spec_region.py
from typing import List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.database import Base, int_pk, str_uniq


class Spec_Region(Base):
    
    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    is_system: Mapped[bool] = mapped_column(default=False, server_default='false')

    # lazy="select" (default) — data/spec_region.py явно подгружает через
    # selectinload(Spec_Region.regions) когда нужно (load_regions=True
    # в /all и в delete-guard сервиса).
    regions: Mapped[List["Region"]] = relationship(
                                                        "Region",
                                                        back_populates="spec_region",
                                                    )
    
    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name}, description={self.description})"

    def __repr__(self):
        return str(self)