"""spec_order_statuses: канон 4 поля (id, name, description, is_default)

Убираем code / is_system / display_order из справочника. Frontend/mobile
берут ру-имя напрямую, никакого code→name маппинга. is_default (partial
unique index) заменяет захардкоженный 'new' в autogen.

Порядок:
  1. ADD COLUMN is_default BOOLEAN NOT NULL DEFAULT false.
  2. UPDATE is_default = true WHERE code = 'new' (пока колонка есть).
  3. Partial unique index — только одна строка is_default = true.
  4. DROP code, is_system, display_order.

Downgrade — восстанавливаем колонки по имени (детерминированный маппинг
для 4 системных строк).

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'a0b1c2d3e4f5'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


# Ру-имя → код (для downgrade — восстановление code-колонки).
NAME_TO_CODE = {
    'Новая':     'new',
    'В работе':  'in_progress',
    'Выполнена': 'completed',
    'Отменена':  'cancelled',
}


def upgrade() -> None:
    # 1. is_default
    op.execute(
        "ALTER TABLE spec_order_statuses "
        "ADD COLUMN is_default BOOLEAN NOT NULL DEFAULT false"
    )

    # 2. Пометить дефолтную по КОДУ (пока код ещё есть).
    op.execute(
        "UPDATE spec_order_statuses SET is_default = true WHERE code = 'new'"
    )

    # 3. Partial unique: только одна строка is_default = true.
    op.execute(
        "CREATE UNIQUE INDEX ix_spec_order_statuses_is_default_true "
        "ON spec_order_statuses (is_default) WHERE is_default = true"
    )

    # 4. DROP колонок — теперь код и служебные флаги не нужны.
    op.execute("ALTER TABLE spec_order_statuses DROP COLUMN code")
    op.execute("ALTER TABLE spec_order_statuses DROP COLUMN is_system")
    op.execute("ALTER TABLE spec_order_statuses DROP COLUMN display_order")


def downgrade() -> None:
    # Восстанавливаем удалённые колонки.
    op.execute(
        "ALTER TABLE spec_order_statuses "
        "ADD COLUMN code VARCHAR, "
        "ADD COLUMN is_system BOOLEAN NOT NULL DEFAULT false, "
        "ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0"
    )

    # Восстанавливаем code + is_system=true для 4 системных строк.
    conn = op.get_bind()
    for order, (name, code) in enumerate(NAME_TO_CODE.items(), start=1):
        conn.execute(
            sa.text(
                "UPDATE spec_order_statuses "
                "SET code = :code, is_system = true, display_order = :ord "
                "WHERE name = :name"
            ),
            {"code": code, "ord": order, "name": name},
        )

    op.execute(
        "ALTER TABLE spec_order_statuses "
        "ALTER COLUMN code SET NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_spec_order_statuses_code "
        "ON spec_order_statuses (code)"
    )
    op.execute("DROP INDEX IF EXISTS ix_spec_order_statuses_is_default_true")
    op.execute("ALTER TABLE spec_order_statuses DROP COLUMN is_default")
