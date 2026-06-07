from typing import List, Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.database import Base, int_pk, str_uniq


class Spec_Priority(Base):
    """Справочник приоритетов неисправностей."""

    id: Mapped[int_pk]
    name: Mapped[str_uniq]   # "Низкий", "Средний", "Высокий", "Критический"
    code: Mapped[str_uniq]   # машинный код: low, medium, high, critical
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_system: Mapped[bool] = mapped_column(default=False, server_default='false')

    issues: Mapped[List["Issue"]] = relationship(
        "Issue",
        back_populates="priority"
    )

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)
