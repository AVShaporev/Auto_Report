"""orders.status: str → status_id INT FK на spec_order_statuses

Продолжение рефакторинга e8f9a0b1c2d3 (справочник spec_order_statuses).
Теперь orders.status становится настоящим FK — по канону как у
Issue/Report со Spec_Status.

DB-representation меняется, API contract НЕ меняется:
  - service/data слой маппит status_code ↔ status_id внутри;
  - Response'ы по-прежнему возвращают status:str через @property на модели;
  - PATCH /order/{id}/status по-прежнему принимает Literal["new",…] код.

Порядок upgrade:
  1. ADD COLUMN status_id INTEGER (nullable) с FK на spec_order_statuses(id).
  2. Backfill: UPDATE orders SET status_id = SELECT id FROM spec_order_statuses
     WHERE code = orders.status.
  3. Defensive: любые NULL после backfill (если в orders.status был мусор,
     не совпадающий со справочником) → default 'new'. В prod'е ожидается
     0 таких строк; но защита нужна чтобы NOT NULL не упал.
  4. ALTER SET NOT NULL.
  5. DROP COLUMN status.

Downgrade — восстанавливаем str-колонку из status_id и её код.

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'f9a0b1c2d3e4'
down_revision = 'e8f9a0b1c2d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add status_id nullable + FK.
    #    Отдельным ALTER чтобы Postgres не пытался валидировать пустые строки
    #    против FK одномоментно (пока пусто — валидация тривиальна).
    op.execute(
        "ALTER TABLE orders ADD COLUMN status_id INTEGER "
        "REFERENCES spec_order_statuses(id)"
    )

    # 2. Backfill из существующей строковой колонки.
    op.execute(
        "UPDATE orders SET status_id = ("
        "  SELECT sos.id FROM spec_order_statuses sos "
        "  WHERE sos.code = orders.status"
        ")"
    )

    # 3. Defensive: любые ордера с status'ом вне справочника → 'new'.
    #    Не должно быть в prod (все живые тенанты только new/in_progress/
    #    completed/cancelled), но на всякий случай.
    op.execute(
        "UPDATE orders SET status_id = ("
        "  SELECT id FROM spec_order_statuses WHERE code = 'new'"
        ") WHERE status_id IS NULL"
    )

    # 4. NOT NULL после того как гарантированно всё заполнено.
    op.execute("ALTER TABLE orders ALTER COLUMN status_id SET NOT NULL")

    # 5. Убираем старую строковую колонку.
    op.execute("ALTER TABLE orders DROP COLUMN status")


def downgrade() -> None:
    # Восстанавливаем строковую колонку и заполняем из справочника.
    op.execute(
        "ALTER TABLE orders ADD COLUMN status VARCHAR DEFAULT 'new'"
    )
    op.execute(
        "UPDATE orders SET status = ("
        "  SELECT code FROM spec_order_statuses WHERE id = orders.status_id"
        ")"
    )
    op.execute("ALTER TABLE orders ALTER COLUMN status SET NOT NULL")
    op.execute("ALTER TABLE orders DROP COLUMN status_id")
