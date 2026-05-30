# model/issue_attachment.py
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk


# Вложение к неисправности: PDF-файл (фото неисправности / документ,
# сконвертированные в один PDF на этапе загрузки).
class Issue_Attachment(Base):

    id: Mapped[int_pk]
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # photo|document|other
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pages: Mapped[int] = mapped_column(default=1, nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    issue: Mapped["Issue"] = relationship(
        "Issue",
        back_populates="attachments",
        lazy="selectin",
    )

    uploader: Mapped["User"] = relationship(
        "User",
        lazy="selectin",
    )

    def __str__(self):
        return f"Issue_Attachment(id={self.id}, issue_id={self.issue_id}, kind={self.kind})"

    def __repr__(self):
        return str(self)
