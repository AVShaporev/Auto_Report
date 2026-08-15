"""spec_order_statuses: справочник статусов заявки на ТО + сид 4 системных строк

Order.status на модели — plain str (без FK). Веб- и мобильный фронты хардкодили
map 'new' → 'Новая', 'in_progress' → 'В работе' и т.п., причём разъехались
(веб: 'Выполнена', мобилка: 'Завершена'). Новая таблица `spec_order_statuses`
даёт единый источник ру-имён + порядок в селектах через API
GET /api/spec_order_status/options.

Миграция чисто аддитивная: без FK на orders.status (соединение soft через
JOIN по коду), без ALTER TABLE orders. Обратимая — downgrade просто дропает
таблицу. Existing строки orders.* остаются как есть, значения кодов
уже совпадают с сидом (new/in_progress/completed/cancelled).

Идемпотентность:
  1. CREATE TABLE IF NOT EXISTS — на случай ручного применения на 192-stage.
  2. INSERT ... ON CONFLICT (code) DO NOTHING — повторный upgrade не дублит.

Revision ID: e8f9a0b1c2d3
Revises: d7f8a9b0c1e2
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'e8f9a0b1c2d3'
down_revision = 'd7f8a9b0c1e2'
branch_labels = None
depends_on = None


# (code, name, display_order)
SPEC_ORDER_STATUSES = [
    ('new',         'Новая',     1),
    ('in_progress', 'В работе',  2),
    ('completed',   'Выполнена', 3),
    ('cancelled',   'Отменена',  4),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS spec_order_statuses (
            id            SERIAL PRIMARY KEY,
            name          VARCHAR NOT NULL UNIQUE,
            code          VARCHAR NOT NULL UNIQUE,
            is_system     BOOLEAN NOT NULL DEFAULT FALSE,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            description   VARCHAR
        )
        """
    )

    conn = op.get_bind()
    for code, name, order in SPEC_ORDER_STATUSES:
        conn.execute(
            sa.text(
                "INSERT INTO spec_order_statuses (code, name, is_system, display_order) "
                "VALUES (:code, :name, TRUE, :display_order) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"code": code, "name": name, "display_order": order},
        )
        # Если строка уже существовала (ручной ALTER до миграции) — промаркируем
        # is_system=TRUE и приведём display_order к каноничному значению.
        conn.execute(
            sa.text(
                "UPDATE spec_order_statuses "
                "SET is_system = TRUE, display_order = :display_order "
                "WHERE code = :code"
            ),
            {"code": code, "display_order": order},
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS spec_order_statuses")
