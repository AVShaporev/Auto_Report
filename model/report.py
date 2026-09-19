from typing import List, Optional, TYPE_CHECKING
from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


# модель отчёта
class Report(Base):
    
    id: Mapped[int_pk]
    number: Mapped[str] = mapped_column(unique=True, nullable=False)
    # FK на spec_report_statuses (миграция f5c6d7e8f9a0). Раньше указывал
    # на общий spec_statuss (тот же, что у Issue), но статусы отчёта
    # {В работе / На утверждении / Утверждён / Отклонён} специфичны —
    # выделили в свой справочник.
    status_id: Mapped[int] = mapped_column(
        ForeignKey("spec_report_statuses.id"),
        nullable=False,
    )
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[date] = mapped_column(default=date.today)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Подпись представителя заказчика узором — простая электронная подпись
    # (миграции e7f8a9b0c1d2, f8a9b0c1d2e3). signature_status: verified |
    # failed; signer_* — снимок ФИО/должности на момент подписания.
    representative_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("customer_representatives.id", ondelete="SET NULL"), nullable=True)
    signature_status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    signature_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    signer_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    signer_position: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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

    # lazy="joined" — JOIN в основном SELECT'е отчётов вместо отдельного
    # selectin'а; автор отчёта почти всегда нужен в ответе и не тащит
    # вложенных коллекций.
    user: Mapped["User"] = relationship(
                                            "User",
                                            back_populates="reports",
                                            lazy="joined"
                                        )

    status: Mapped["Spec_Report_Status"] = relationship(
        "Spec_Report_Status",
        lazy="joined",
    )

    order: Mapped[Optional["Order"]] = relationship(
                                                        "Order",
                                                        back_populates="report",
                                                        lazy="selectin",
                                                        uselist=False
                                                    )

    # lazy="select" (default) — большие списки не должны тащить attachments.
    # data/report.py использует raiseload(Report.attachments) для list/all,
    # detail-view явно selectinload-ит attachments при load_attachments=True.
    attachments: Mapped[List["Report_Attachment"]] = relationship(
        "Report_Attachment",
        back_populates="report",
        cascade="all, delete-orphan",
    )

    @property
    def is_signed(self) -> bool:
        return self.signature_status == "verified"

    def __str__(self):
        return f"Report(id={self.id}, number={self.number})"

    def __repr__(self):
        return str(self)