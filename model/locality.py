from typing import List
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

from model.spec_locality import Spec_Locality

class Locality(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    spec_locallity_id: Mapped[int] = mapped_column(ForeignKey("spec_localitys.id"))

    # один населенный пункт - один тип населенного пункта
    spec_locality: Mapped[Spec_Locality] = relationship(Spec_Locality)