"""issues.number: VARCHAR(50) → VARCHAR(200)

Реальный шаблон генерации `service/issue.py::create_issue`:
  "{number_in_contract}/{MM}/{YYYY}/{customer.short_name}/{contract.short_subject}/Н/{seq}"

Long short_customer/short_subject у tenant'а легко переваливают за 50
символов (демо-стенд 2026-09-13 ловил StringDataRightTruncationError
на POST /api/issue/create). Аналог orders.number (уже VARCHAR(200)).

Revision ID: a3c4d5e6f7b8
Revises: f9a0b1c2d3e4
Create Date: 2026-09-13
"""
from alembic import op
import sqlalchemy as sa


revision = 'a3c4d5e6f7b8'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'issues',
        'number',
        existing_type=sa.String(length=50),
        type_=sa.String(length=200),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Осторожно: если в таблице уже есть номера длиннее 50 — downgrade
    # обрежет их и сломает уникальность. Перед downgrade нужен ручной
    # аудит: SELECT id, number FROM issues WHERE LENGTH(number) > 50.
    op.alter_column(
        'issues',
        'number',
        existing_type=sa.String(length=200),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
