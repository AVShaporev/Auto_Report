"""add is_protected to roles and users

Защита bootstrap-роли и юзера от удаления/модификации через UI.

Семантика:
- `roles.is_protected = TRUE` → service.role.delete_role и update_role
  возвращают 400. Используется для роли `superadmin` (создаётся
  bootstrap_admin.py).
- `users.is_protected = TRUE` → service.user.delete_user возвращает 400;
  update_user разрешает только смену личных полей (full_name, email,
  phone, telegram_id, password), запрещает name, role_id, is_active.

Идемпотентность: server_default='false' на колонке, UPDATE по name —
если bootstrap уже отработал и юзера/роли нет, UPDATE матчит 0 строк
и не падает.

Revision ID: d4f8e3c7b2a1
Revises: c1f4a7e3d9b2
Create Date: 2026-06-13
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4f8e3c7b2a1'
down_revision = 'c1f4a7e3d9b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'roles',
        sa.Column(
            'is_protected',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'users',
        sa.Column(
            'is_protected',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )

    conn = op.get_bind()

    # Помечаем bootstrap superadmin как защищённую запись.
    # При первом накатывании на свежую БД (bootstrap ещё не запускался)
    # UPDATE матчит 0 строк — это OK, bootstrap_admin.py поставит
    # is_protected=True самостоятельно при создании.
    conn.execute(sa.text(
        "UPDATE roles SET is_protected = TRUE WHERE name = 'superadmin'"
    ))
    conn.execute(sa.text(
        "UPDATE users SET is_protected = TRUE WHERE name = 'superadmin'"
    ))


def downgrade() -> None:
    op.drop_column('users', 'is_protected')
    op.drop_column('roles', 'is_protected')
