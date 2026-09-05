"""Due-date: SLA-поля Spec_Order + Order.due_date + Report.status_id FK
на spec_report_statuses (вместо spec_statuss).

Три вещи в одной миграции:

1. Spec_Order:
   - sla_kind VARCHAR(20) NOT NULL DEFAULT 'manual'
     - 'periodic'      — по окончанию календарного периода (monthly / quarterly / ...)
     - 'from_creation' — created_at + sla_days
     - 'manual'        — юзер вводит вручную
   - sla_days INTEGER NULL — только для 'from_creation'
   Backfill:
     is_default_planned=true → 'periodic', sla_days=NULL
     is_default_primary=true → 'from_creation', sla_days=3 (АВР по-умолчанию)
     остальные              → 'manual'

2. Order.due_date DATE NULL. Backfill открытых заявок (WHERE report_id IS NULL):
   - Если тип 'periodic' — до конца календарного периода от period_start_date
     (или от created_at если period_start_date NULL), по period_code объекта.
   - Если тип 'from_creation' — created_at + spec_order.sla_days.
   - Если тип 'manual' — NULL.

3. Report.status_id: DROP FK на spec_statuss, ADD FK на spec_report_statuses.
   Backfill: все Report.status_id заменяем на дефолтный id из
   spec_report_statuses (is_default=true) — что означает «В работе».
   Более точный маппинг по имени старых статусов не делаем — исторические
   данные всё равно неполные, а «В работе» — безопасный старт.

Revision ID: f5c6d7e8f9a0
Revises: f4b5c6d7e8f9
Create Date: 2026-09-05
"""
from datetime import date, timedelta
from calendar import monthrange
from typing import Optional

from alembic import op
import sqlalchemy as sa


revision = 'f5c6d7e8f9a0'
down_revision = 'f4b5c6d7e8f9'
branch_labels = None
depends_on = None


def _period_end(period_code: Optional[str], anchor: date) -> Optional[date]:
    """Конец календарного периода, содержащего дату `anchor`.

    monthly    → последний день месяца anchor
    quarterly  → последний день квартала (месяцы 3/6/9/12)
    semiannual → 30 июня или 31 декабря
    yearly     → 31 декабря
    None/custom → None
    """
    if not period_code or period_code == 'custom':
        return None
    if period_code == 'monthly':
        last = monthrange(anchor.year, anchor.month)[1]
        return date(anchor.year, anchor.month, last)
    if period_code == 'quarterly':
        q_end_month = ((anchor.month - 1) // 3) * 3 + 3
        last = monthrange(anchor.year, q_end_month)[1]
        return date(anchor.year, q_end_month, last)
    if period_code == 'semiannual':
        if anchor.month <= 6:
            return date(anchor.year, 6, 30)
        return date(anchor.year, 12, 31)
    if period_code == 'yearly':
        return date(anchor.year, 12, 31)
    return None


def upgrade() -> None:
    conn = op.get_bind()

    # ---------- 1. Spec_Order SLA-поля ----------
    op.execute(
        "ALTER TABLE spec_orders "
        "ADD COLUMN sla_kind VARCHAR(20) NOT NULL DEFAULT 'manual'"
    )
    op.execute("ALTER TABLE spec_orders ADD COLUMN sla_days INTEGER")

    # Backfill по is_default_* флагам.
    op.execute(
        "UPDATE spec_orders SET sla_kind = 'periodic' "
        "WHERE is_default_planned = true"
    )
    op.execute(
        "UPDATE spec_orders SET sla_kind = 'from_creation', sla_days = 3 "
        "WHERE is_default_primary = true"
    )

    # CHECK: sla_days обязателен для 'from_creation', запрещён для остальных.
    op.execute(
        "ALTER TABLE spec_orders ADD CONSTRAINT spec_orders_sla_days_valid "
        "CHECK ("
        "  (sla_kind = 'from_creation' AND sla_days IS NOT NULL AND sla_days > 0) OR "
        "  (sla_kind <> 'from_creation' AND sla_days IS NULL)"
        ")"
    )
    op.execute(
        "ALTER TABLE spec_orders ADD CONSTRAINT spec_orders_sla_kind_valid "
        "CHECK (sla_kind IN ('periodic', 'from_creation', 'manual'))"
    )

    # ---------- 2. Order.due_date ----------
    op.execute("ALTER TABLE orders ADD COLUMN due_date DATE")

    # Backfill открытых заявок (без отчёта).
    # Тянем сразу все нужные поля через JOIN'ы, считаем в Python (для дат
    # проще, чем городить PL/pgSQL с monthrange).
    rows = conn.execute(sa.text(
        "SELECT o.id, o.created_at, o.period_start_date, "
        "       so.sla_kind, so.sla_days, "
        "       p.code AS period_code "
        "FROM orders o "
        "JOIN spec_orders so ON so.id = o.spec_order_id "
        "JOIN objects obj    ON obj.id = o.object_id "
        "LEFT JOIN periods p ON p.id = obj.period_id "
        "WHERE o.report_id IS NULL"
    )).fetchall()

    for row in rows:
        due: Optional[date] = None
        if row.sla_kind == 'periodic':
            anchor = row.period_start_date or row.created_at
            due = _period_end(row.period_code, anchor)
        elif row.sla_kind == 'from_creation' and row.sla_days:
            due = row.created_at + timedelta(days=row.sla_days)
        # 'manual' → due остаётся None

        if due is not None:
            conn.execute(
                sa.text("UPDATE orders SET due_date = :d WHERE id = :id"),
                {"d": due, "id": row.id},
            )

    # ---------- 3. Report.status_id → spec_report_statuses ----------
    default_report_status_id = conn.execute(
        sa.text("SELECT id FROM spec_report_statuses WHERE is_default = true LIMIT 1")
    ).scalar()
    if default_report_status_id is None:
        raise RuntimeError(
            "spec_report_statuses не имеет is_default=true — миграция "
            "f3a4b5c6d7e8 не выполнена или seed сломан."
        )

    # Найти имя FK-констрейнта на spec_statuss (может быть автосгенерированным).
    fk_name = conn.execute(sa.text(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid = 'reports'::regclass "
        "  AND contype = 'f' "
        "  AND pg_get_constraintdef(oid) LIKE '%REFERENCES spec_statuss%'"
    )).scalar()
    if fk_name:
        op.execute(f'ALTER TABLE reports DROP CONSTRAINT "{fk_name}"')

    # Backfill: все существующие Report.status_id → default (В работе).
    conn.execute(
        sa.text("UPDATE reports SET status_id = :d"),
        {"d": default_report_status_id},
    )

    op.execute(
        "ALTER TABLE reports ADD CONSTRAINT reports_status_id_fkey "
        "FOREIGN KEY (status_id) REFERENCES spec_report_statuses(id)"
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Report.status_id — обратно на spec_statuss. Ставим id=1 (первый из
    # spec_statuss), это исторический default. Если таблица пустая — 1
    # может не существовать; downgrade безопасен только если spec_statuss
    # содержит валидные строки.
    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_status_id_fkey")
    fallback = conn.execute(
        sa.text("SELECT id FROM spec_statuss ORDER BY id LIMIT 1")
    ).scalar()
    if fallback is not None:
        conn.execute(
            sa.text("UPDATE reports SET status_id = :d"),
            {"d": fallback},
        )
    op.execute(
        "ALTER TABLE reports ADD CONSTRAINT reports_status_id_fkey "
        "FOREIGN KEY (status_id) REFERENCES spec_statuss(id)"
    )

    # Order.due_date
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS due_date")

    # Spec_Order SLA
    op.execute("ALTER TABLE spec_orders DROP CONSTRAINT IF EXISTS spec_orders_sla_kind_valid")
    op.execute("ALTER TABLE spec_orders DROP CONSTRAINT IF EXISTS spec_orders_sla_days_valid")
    op.execute("ALTER TABLE spec_orders DROP COLUMN IF EXISTS sla_days")
    op.execute("ALTER TABLE spec_orders DROP COLUMN IF EXISTS sla_kind")
