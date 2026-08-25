"""activity_logs.description — забытая Base-col (v1.0.15)

Родная миграция c2f5b8a3d941 упустила колонку `description` (nullable),
которую `Base` добавляет на каждой модели. SQLAlchemy включает её в
SELECT, backend падает `column activity_logs.description does not exist`.

Тот же паттерн: см. c5e6f7a8b9c0 (idempotency_keys) и d7f8a9b0c1e2
(media_upload_sessions). Тема известная — ссылка на feedback-заметку
`[[autoreport-alembic-base-cols]]` (TODO).

Revision ID: c8a4d3e2f9b7
Revises: c2f5b8a3d941
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa


revision = "c8a4d3e2f9b7"
down_revision = "c2f5b8a3d941"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activity_logs",
        sa.Column("description", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("activity_logs", "description")
