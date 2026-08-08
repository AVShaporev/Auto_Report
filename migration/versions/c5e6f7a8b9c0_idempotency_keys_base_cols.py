"""idempotency_keys: добавить Base-колонки updated_at + description

Миграция b3c4d5e6f7a8 создала таблицу без updated_at/description, а модель
IdempotencyKey наследует их от Base (см. database/database.py). Из-за этого
ORM SELECT падает: `column idempotency_keys.updated_at does not exist`.
IdempotencyMiddleware ловит эту ошибку на каждом POST/PUT/PATCH/DELETE с
X-Idempotency-Key → 500 → CORS-заголовки не долетают → на мобилке
"Network Error".

Revision ID: c5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa


revision = 'c5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'idempotency_keys',
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.add_column(
        'idempotency_keys',
        sa.Column('description', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('idempotency_keys', 'description')
    op.drop_column('idempotency_keys', 'updated_at')
