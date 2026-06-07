from typing import List

from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


class Spec_System(Base):
    """
    Справочник типов обслуживаемых систем.

    Поле is_fire_protection — признак принадлежности к средствам и системам
    противопожарной защиты.
    """

    __tablename__ = "spec_systems"

    id: Mapped[int_pk]
    name: Mapped[str_uniq] = mapped_column(comment="Наименование типа системы")
    short_name: Mapped[str_null_true] = mapped_column(comment="Сокращённое наименование")
    is_fire_protection: Mapped[bool] = mapped_column(
        default=False,
        comment="Принадлежность к средствам и системам противопожарной защиты",
    )
    is_system: Mapped[bool] = mapped_column(default=False, server_default='false')

    objects_equipments: Mapped[List["Objects_Equipment"]] = relationship(
        "Objects_Equipment",
        back_populates="spec_system",
        lazy="selectin",
    )

    def __str__(self):
        return f"Spec_System(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)
