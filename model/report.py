from typing import List, Optional, TYPE_CHECKING
from datetime import date

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


# модель отчёта
class Report(Base):
    
    id: Mapped[int_pk]
    number: Mapped[str] = mapped_column(unique=True, nullable=False)
    status_id: Mapped[int] = mapped_column(
        ForeignKey("spec_statuss.id"),
        nullable=False,
    )
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[date] = mapped_column(default=date.today)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Все отношения через строки
    period: Mapped["Period"] = relationship(
                                                "Period",
                                                back_populates="reports",
                                                lazy="selectin"
                                            )

    contract: Mapped["Contract"] = relationship(
                                                    "Contract",
                                                    back_populates="reports",
                                                    lazy="selectin"
                                                )

    object: Mapped["Object"] = relationship(
                                                "Object",
                                                back_populates="reports",
                                                lazy="selectin"
                                            )

    user: Mapped["User"] = relationship(
                                            "User",
                                            back_populates="reports",
                                            lazy="selectin"
                                        )

    status: Mapped["Spec_Status"] = relationship(
        "Spec_Status",
        back_populates="reports",
        lazy="selectin",
    )

    order: Mapped[Optional["Order"]] = relationship(
                                                        "Order",
                                                        back_populates="report",
                                                        lazy="selectin",
                                                        uselist=False
                                                    )

    attachments: Mapped[List["Report_Attachment"]] = relationship(
        "Report_Attachment",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __str__(self):
        return f"Report(id={self.id}, number={self.number})"

    def __repr__(self):
        return str(self)