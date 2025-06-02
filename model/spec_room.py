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
import model.organization import Organization


class Spec_Room(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]

    # к одному типу комнаты может относится много организаций
    organizations: Mapped[List[Organization]] = relationship(Organization,
                                                    back_populates="spec_room")

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)