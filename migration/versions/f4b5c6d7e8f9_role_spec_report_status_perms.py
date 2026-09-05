"""role: 4 флага spec_report_status_read/create/modify/delete

CRUD-endpoints для нового справочника статусов отчёта требуют явные права
роли. По образцу b1c2d3e4f5a6 (spec_order_status_*).

Revision ID: f4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-09-05
"""
from alembic import op


revision = 'f4b5c6d7e8f9'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


PERMS = [
    'spec_report_status_read',
    'spec_report_status_create',
    'spec_report_status_modify',
    'spec_report_status_delete',
]


def upgrade() -> None:
    for perm in PERMS:
        op.execute(
            f"ALTER TABLE roles ADD COLUMN {perm} BOOLEAN NOT NULL DEFAULT false"
        )

    # Superadmin — все права. Admin — READ по-умолчанию.
    for perm in PERMS:
        op.execute(
            f"UPDATE roles SET {perm} = true WHERE is_superadmin = true"
        )
    op.execute(
        "UPDATE roles SET spec_report_status_read = true "
        "WHERE is_admin = true AND is_superadmin = false"
    )


def downgrade() -> None:
    for perm in PERMS:
        op.execute(f"ALTER TABLE roles DROP COLUMN IF EXISTS {perm}")
