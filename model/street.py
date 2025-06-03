from datetime import date
from typing import List

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
from model.organization import Organization
from model.spec_street import Spec_Street

class Street(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    spec_street_id: Mapped[int] = mapped_column(ForeignKey("spec_streets.id")) # тип улицы

    # у улицы может быть только один тип улицы
    spec_street: Mapped[Spec_Street] = relationship(Spec_Street,
                                                        back_populates="streets")

    # на одной улице может быть много организаций
    organizations: Mapped[List[Organization]] = relationship(Organization,
                                                                back_populates="street")

    # на одной улице может быть много объектов
    objects: Mapped[List[Object]] = relationship(Object,
                                                    back_populates="street")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)


