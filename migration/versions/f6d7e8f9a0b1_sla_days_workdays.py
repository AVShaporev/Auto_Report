"""spec_orders.sla_days_workdays — календарные vs рабочие дни для SLA

Расширение SLA from_creation: если workdays=TRUE, sla_days считается в
рабочих днях (пропускаем сб/вс, праздники НЕ учитываем — простой вариант
без внешнего справочника).

Default FALSE — обратная совместимость: существующие типы с sla_kind=
'from_creation' продолжают считать в календарных днях.

Revision ID: f6d7e8f9a0b1
Revises: f5c6d7e8f9a0
Create Date: 2026-09-05
"""
from alembic import op


revision = 'f6d7e8f9a0b1'
down_revision = 'f5c6d7e8f9a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE spec_orders "
        "ADD COLUMN sla_days_workdays BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE spec_orders DROP COLUMN IF EXISTS sla_days_workdays")
