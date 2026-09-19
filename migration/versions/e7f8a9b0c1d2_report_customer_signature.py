"""reports: подпись заказчика (этап 1.2 плана после анализа конкурентов)

Заказчик расписывается пальцем на телефоне инженера в форме отчёта. Картинка
(PNG) — файл в MEDIA/reports/<id>/, в таблице путь, ФИО и должность
подписавшего и время подписания. В акте — метка {{ customer_signature }}.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-09-19
"""
from alembic import op
import sqlalchemy as sa


revision = "e7f8a9b0c1d2"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("signature_path", sa.String(length=500), nullable=True))
    op.add_column("reports", sa.Column("signer_name", sa.String(length=150), nullable=True))
    op.add_column("reports", sa.Column("signer_position", sa.String(length=150), nullable=True))
    op.add_column("reports", sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "signed_at")
    op.drop_column("reports", "signer_position")
    op.drop_column("reports", "signer_name")
    op.drop_column("reports", "signature_path")
