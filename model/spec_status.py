from typing import List

from sqlalchemy.orm import (
                            Mapped,
                            mapped_column,
                            relationship
)
from database.database import (
                                Base,
                                int_pk,
                                str_uniq
)

# модель статуса неисправности (справочник)
class Spec_Status(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]   # отображаемое наименование: "Новая", "В работе", ...
    code: Mapped[str_uniq]   # машинный код: new, in_progress, resolved, closed
    is_system: Mapped[bool] = mapped_column(default=False, server_default='false')

    issues: Mapped[List["Issue"]] = relationship(
        "Issue",
        back_populates="status"
    )

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)
