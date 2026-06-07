"""make user contact fields nullable

Делает поля full_name/email/phone/telegram_id у users NULL-able.
Раньше они были NOT NULL из-за `Mapped[str] = None` в модели.

Revision ID: a1b2c3d4e5f6
Revises: 70daa6ea31f5
Create Date: 2026-06-07

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "70daa6ea31f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "full_name", nullable=True)
    op.alter_column("users", "email", nullable=True)
    op.alter_column("users", "phone", nullable=True)
    op.alter_column("users", "telegram_id", nullable=True)


def downgrade() -> None:
    op.alter_column("users", "telegram_id", nullable=False)
    op.alter_column("users", "phone", nullable=False)
    op.alter_column("users", "email", nullable=False)
    op.alter_column("users", "full_name", nullable=False)
