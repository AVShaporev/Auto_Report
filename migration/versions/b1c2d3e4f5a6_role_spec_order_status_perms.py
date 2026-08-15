"""role: 4 флага spec_order_status_read/create/modify/delete

CRUD-endpoints для справочника статусов заявок теперь требуют явные
права роли. Superadmin (is_superadmin=true) — автоматом получает всё
(на уровне сервиса), но реальные строки прав тоже проставим true для
консистентности с другими spec_*.

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'b1c2d3e4f5a6'
down_revision = 'a0b1c2d3e4f5'
branch_labels = None
depends_on = None


PERMS = [
    'spec_order_status_read',
    'spec_order_status_create',
    'spec_order_status_modify',
    'spec_order_status_delete',
]


def upgrade() -> None:
    for perm in PERMS:
        op.execute(
            f"ALTER TABLE roles ADD COLUMN {perm} BOOLEAN NOT NULL DEFAULT false"
        )

    # Superadmin получает все spec_order_status_* права.
    for perm in PERMS:
        op.execute(
            f"UPDATE roles SET {perm} = true WHERE is_superadmin = true"
        )

    # Ролям admin (is_admin=true но не super) даём READ по-умолчанию —
    # чтобы просмотр справочника не требовал ручного включения.
    op.execute(
        "UPDATE roles SET spec_order_status_read = true "
        "WHERE is_admin = true AND is_superadmin = false"
    )


def downgrade() -> None:
    for perm in PERMS:
        op.execute(f"ALTER TABLE roles DROP COLUMN IF EXISTS {perm}")
