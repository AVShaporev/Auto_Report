"""fix spec_journals — add missing created_at / updated_at

В миграции b8e2f4a6d5c3 при создании таблицы spec_journals не были
добавлены колонки `created_at` и `updated_at`, которые автоматически
наследуются от `Base` (см. database.database.Base). Из-за этого
SQLAlchemy при SELECT падал с UndefinedColumnError.

Доливаем обе колонки NOT NULL с server_default=NOW(), чтобы заодно
заполнить уже существующие строки (системный `maintenance`).

Revision ID: c1f4a7e3d9b2
Revises: b8e2f4a6d5c3
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa


revision = 'c1f4a7e3d9b2'
down_revision = 'b8e2f4a6d5c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'spec_journals',
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        'spec_journals',
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_column('spec_journals', 'updated_at')
    op.drop_column('spec_journals', 'created_at')
