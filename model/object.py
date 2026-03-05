# model/object.py
from typing import List, Optional, TYPE_CHECKING
from datetime import date

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


# модель объекта
class Object(Base):
    
    id: Mapped[int_pk]
    name: Mapped[str]
    build_number: Mapped[str_null_true]
    room_number: Mapped[str_null_true]
    responsible_face: Mapped[str]
    responsible_faces_contact: Mapped[str]
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    arial_id: Mapped[int] = mapped_column(ForeignKey("arials.id"))
    locality_id: Mapped[int] = mapped_column(ForeignKey("localitys.id"))
    street_id: Mapped[int] = mapped_column(ForeignKey("streets.id"))
    spec_build_id: Mapped[int] = mapped_column(ForeignKey("spec_builds.id"))
    spec_room_id: Mapped[int] = mapped_column(ForeignKey("spec_rooms.id"))
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"))
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))

    # Все отношения через строки
    region: Mapped["Region"] = relationship(
                                                "Region",
                                                back_populates="objects",
                                                lazy="selectin"
                                            )

    arial: Mapped["Arial"] = relationship(
                                                "Arial",
                                                back_populates="objects",
                                                lazy="selectin"
                                            )

    locality: Mapped["Locality"] = relationship(
                                                    "Locality",
                                                    back_populates="objects",
                                                    lazy="selectin"
                                                )

    street: Mapped["Street"] = relationship(
                                                "Street",
                                                back_populates="objects",
                                                lazy="selectin"
                                            )
    
    spec_build: Mapped["Spec_Build"] = relationship(
                                                        "Spec_Build",
                                                        back_populates="objects",
                                                        lazy="selectin"
                                                    )

    spec_room: Mapped["Spec_Room"] = relationship(
                                                    "Spec_Room",
                                                    back_populates="objects",
                                                    lazy="selectin"
                                                )

    period: Mapped["Period"] = relationship(
                                                "Period",
                                                back_populates="objects",
                                                lazy="selectin"
                                            )

    contract: Mapped["Contract"] = relationship(
                                                    "Contract",
                                                    back_populates="objects",
                                                    lazy="selectin"
                                                )

    objects_equipments: Mapped[List["Objects_Equipment"]] = relationship(
                                                                            "Objects_Equipment",
                                                                            back_populates="objects",
                                                                            lazy="selectin"
                                                                        )

    reports: Mapped[List["Report"]] = relationship(
                                                        "Report",
                                                        back_populates="object",
                                                        lazy="selectin"
                                                    )

    orders: Mapped[List["Order"]] = relationship(
                                                    "Order",
                                                    back_populates="object",
                                                    lazy="selectin"
                                                )

    def __str__(self):
        return f"Object(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)