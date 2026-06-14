# model/period.py
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.database import Base, int_pk, str_uniq


# модель периода обслуживания
class Period(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    period: Mapped[str_uniq]
    # Календарный код для авто-генерации плановых заявок:
    #   monthly    — 1-е число каждого месяца
    #   quarterly  — 1 января/апреля/июля/октября
    #   semiannual — 1 января, 1 июля
    #   yearly     — 1 января
    #   custom     — авто-tick не работает (для прежних/ручных периодов)
    code: Mapped[Optional[str]] = mapped_column(nullable=True)

    # ✅ Правильное отношение с back_populates
    objects: Mapped[List["Object"]] = relationship(
                                                    "Object",
                                                    back_populates="period",
                                                    lazy="selectin"
                                                    )

    reports: Mapped[List["Report"]] = relationship(
                                                    "Report",
                                                    back_populates="period",
                                                    lazy="selectin"
                                                    )

    operations: Mapped[List["Operation"]] = relationship(
        "Operation",
        back_populates="period",
        lazy="selectin",
    )

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)

# Импорт после определения
from model.object import Object