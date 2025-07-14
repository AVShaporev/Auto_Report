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
# from model.region import Region
from model.arial import Arial
from model.locality import Locality
from model.street import Street
from model.spec_build import Spec_Build
from model.spec_room import Spec_Room
from model.period import Period
from model.contract import Contract
from model.objects_equipment import Objects_Equipment
from model.report import Report


class Object(Base):

    id: Mapped[int_pk]
    name: Mapped[str]
    build_number: Mapped[str_null_true]
    room_number: Mapped[str_null_true]
    responsible_face: Mapped[str]
    responsible_faces_contact: Mapped[str]
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))            # регион
    arial_id: Mapped[int] = mapped_column(ForeignKey("arials.id"))              # район
    locality_id: Mapped[int] = mapped_column(ForeignKey("localitys.id"))        # населенный пункт
    street_id: Mapped[int] = mapped_column(ForeignKey("streets.id"))            # улица
    spec_build_id: Mapped[int] = mapped_column(ForeignKey("spec_builds.id"))    # тип строения
    spec_room_id: Mapped[int] = mapped_column(ForeignKey("spec_rooms.id"))      # тип помещения
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"))            # период обслуживания
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))        # контракт

    # объект может находиться только в одном регионе (один к одному)
    region: Mapped["Region"] = relationship("Region",
                                            back_populates="objects",
                                                            lazy="selectin")

    # объект может находиться только в одном районе (один к одному)
    arial: Mapped["Arial"] = relationship("Arial",
                                            back_populates="objects",
                                                            lazy="selectin")

    # объект может находиться только в одном нас.пункте (один к оддному)
    locality: Mapped[Locality] = relationship(Locality,
                                            back_populates="objects",
                                                            lazy="selectin")

    # объект может быть только на одной улице (один к одному)
    street: Mapped[Street] = relationship(Street,
                                            back_populates="objects",
                                                            lazy="selectin")
    
    # наименование типа строения (один к одному)
    spec_build: Mapped[Spec_Build] = relationship(Spec_Build,
                                                    lazy="selectin")

    # наименование типа помещения (один к одному)
    spec_room: Mapped[Spec_Room] = relationship(Spec_Room,
                                                    lazy="selectin")

    # наименование периода обслуживания (один к одному)
    period: Mapped[Period] = relationship(Period,
                                            lazy="selectin")

    # объект может быть только в одном контракте (один к одному)
    contract: Mapped[Contract] = relationship(Contract,
                                            back_populates="objects",
                                                            lazy="selectin")

    # наименование оборудования на одному объекте может быть несколько (один ко многим)
    objects_equipments: Mapped[List[Objects_Equipment]] = relationship(Objects_Equipment,
                                                                        back_populates="objects",
                                                                        lazy="selectin")

    # отчеты по объекту (один объект много отчетов - один ко многим)
    reports: Mapped[List[Report]] = relationship(Report,
                                                    back_populates="object_report",
                                                    lazy="selectin")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)