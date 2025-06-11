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
from model.bank import Bank
from model.region import Region
# from model.arial import Arial
from model.locality import Locality
from model.street import Street
from model.spec_build import Spec_Build
from model.spec_room import Spec_Room
from model.spec_job_title import Spec_Job_Title



class Organization(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    short_name: Mapped[str_uniq]
    inn: Mapped[str_uniq]
    kpp: Mapped[str]
    director_first_name: Mapped[str]
    drector_last_name: Mapped[str]
    drector_surname: Mapped[str]
    email: Mapped[str_null_true]
    telephone: Mapped[str_null_true]
    site: Mapped[str_null_true]
    corr_check: Mapped[str]
    acc_check: Mapped[str]
    build_number: Mapped[str_null_true]
    room_number: Mapped[str_null_true]
    customer: Mapped[bool]
    executor: Mapped[bool]
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"))                # банк
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))            # субъект РФ
    arial_id: Mapped[int] = mapped_column(ForeignKey("arials.id"))              # район
    locality_id: Mapped[int] = mapped_column(ForeignKey("localitys.id"))        # населенный пункт
    street_id: Mapped[int] = mapped_column(ForeignKey("streets.id"))            # улица
    spec_build_id: Mapped[int] = mapped_column(ForeignKey("spec_builds.id"))    # тип строения
    spec_room_id: Mapped[int] = mapped_column(ForeignKey("spec_rooms.id"))      # тип помещения
    spec_job_title_id: Mapped[int] = mapped_column(ForeignKey("spec_job_titles.id"))    # должность руководителя

    # банк
    bank: Mapped[Bank] = relationship(Bank,
                                        back_populates="organizations",
                                        lazy="selectin")
    
    # регион
    region: Mapped[Region] = relationship(Region,
                                            back_populates="organizations",
                                            lazy="selectin")

    # район
    arial: Mapped["Arial"] = relationship("Arial",
                                            back_populates="organizations",
                                            lazy="selectin")

    # нас. пункт
    locality: Mapped[Locality] = relationship(Locality,
                                                back_populates="organizations",
                                                lazy="selectin")

    # улица
    street: Mapped[Street] = relationship(Street,
                                            back_populates="organizations",
                                            lazy="selectin")
    
    # тип строения
    spec_build: Mapped[Spec_Build] = relationship(Spec_Build,
                                            back_populates="organizations",
                                            lazy="selectin")

    # тип помещения
    spec_room: Mapped[Spec_Room] = relationship(Spec_Room,
                                            back_populates="organizations",
                                            lazy="selectin")

    # должность руководителя
    spec_job_title: Mapped[Spec_Job_Title] = relationship(Spec_Job_Title,
                                                            back_populates="organizations",
                                                            lazy="selectin")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)