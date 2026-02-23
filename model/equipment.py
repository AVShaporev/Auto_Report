from typing import List, TYPE_CHECKING
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


from model.spec_equipment import Spec_Equipment
# from model.objects_equipment import Objects_Equipment


class Equipment(Base):
    
    __table_args__ = {"extend_existing":True}

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    spec_equipment_id: Mapped[int] = mapped_column(ForeignKey("spec_equipments.id"))   # тип оборудования

    # одно наименование оборудования относится к одному типу оборудования
    spec_equipment: Mapped["Spec_Equipment"] = relationship(
                                                                "Spec_Equipment",
                                                                back_populates="equipments",  # ✅ Должно совпадать с полем в Spec_Equipment
                                                                lazy="selectin"
                                                            )

    # наименование оборудования на объекте
    objects_equipment: Mapped["Objects_Equipment"] = relationship("Objects_Equipment",
                                                                    lazy="selectin",
                                                                    back_populates="equipments")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)



