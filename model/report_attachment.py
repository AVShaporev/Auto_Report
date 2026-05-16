# model/report_attachment.py
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk


# Вложение к отчёту: PDF-файл (фото подписанного акта/журнала/оборудования и т.п.,
# сконвертированные в один PDF на этапе загрузки).
class Report_Attachment(Base):

    id: Mapped[int_pk]
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # act|journal|equipment|other
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pages: Mapped[int] = mapped_column(default=1, nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    report: Mapped["Report"] = relationship(
        "Report",
        back_populates="attachments",
        lazy="selectin",
    )

    uploader: Mapped["User"] = relationship(
        "User",
        lazy="selectin",
    )

    def __str__(self):
        return f"Report_Attachment(id={self.id}, report_id={self.report_id}, kind={self.kind})"

    def __repr__(self):
        return str(self)
