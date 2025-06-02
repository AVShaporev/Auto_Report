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
from model.street import Street


class Spec_Street(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]

    # к одному типу улицы может относится несколько улиц
    streets: Mapped[List[Street]] = relationship(Street,
                                                    back_populates="spec_street")