"""role.user_onboard_mobile — право выдавать QR для входа в mobile

Revision ID: e2b3c4d5f6a7
Revises: d1a2b3c4e5f6
Create Date: 2026-08-28

Новое право RBAC: только с ним админ может сгенерировать QR / ссылку
для входа юзера в mobile-приложение (перенос функции из master в
tenant-web-UI). Дефолт `False` для всех новых ролей.

Backfill: `is_admin=TRUE` и `is_superadmin=TRUE` роли получают
`TRUE` при накатывании — иначе после релиза у них пропадёт функция
«📱 QR» пока они себе не проставят вручную.
"""
from alembic import op
import sqlalchemy as sa


revision = "e2b3c4d5f6a7"
down_revision = "d1a2b3c4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column(
            "user_onboard_mobile",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        "UPDATE roles SET user_onboard_mobile = TRUE "
        "WHERE is_admin = TRUE OR is_superadmin = TRUE"
    )


def downgrade() -> None:
    op.drop_column("roles", "user_onboard_mobile")
