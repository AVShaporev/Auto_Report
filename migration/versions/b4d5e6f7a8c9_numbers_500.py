"""orders.number, issues.number: VARCHAR(200) → VARCHAR(500)

Номера генерируются сервером:
  заявка:        "{number_in_contract}/{MM}/{YYYY}/{customer.short_name}/{contract.short_subject}/{spec_order.short_name}/{seq}"
  неисправность: "{number_in_contract}/{MM}/{YYYY}/{customer.short_name}/{contract.short_subject}/Н/{seq}"

При лимитах схем на исходники (short_name ≤ 100, short_subject ≤ 200,
spec_order.short_name ≤ 50) номер доходит до ~375 символов — в VARCHAR(200)
не влезал (StringDataRightTruncation → 500 на INSERT). reports.number в БД
без ограничения длины, его не трогаем.

В Postgres расширение VARCHAR — изменение метаданных, без перезаписи таблицы.

Revision ID: b4d5e6f7a8c9
Revises: a3c4d5e6f7b8
Create Date: 2026-09-14
"""
from alembic import op
import sqlalchemy as sa


revision = 'b4d5e6f7a8c9'
down_revision = 'a3c4d5e6f7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ('orders', 'issues'):
        op.alter_column(
            table,
            'number',
            existing_type=sa.String(length=200),
            type_=sa.String(length=500),
            existing_nullable=False,
        )


def downgrade() -> None:
    # Осторожно: номера длиннее 200 символов не влезут обратно. Перед downgrade
    # проверить: SELECT id, number FROM orders WHERE LENGTH(number) > 200
    # (и то же для issues).
    for table in ('orders', 'issues'):
        op.alter_column(
            table,
            'number',
            existing_type=sa.String(length=500),
            type_=sa.String(length=200),
            existing_nullable=False,
        )
