"""spec_report_statuses: справочник статусов отчёта + сид 4 системных строк

По образцу spec_order_statuses (миграция e8f9a0b1c2d3 + канон a0b1c2d3e4f5),
но сразу в каноничном виде (без code/is_system/display_order). Только id,
name, description (из Base), is_default.

Статусы (workflow отчёта):
    - «В работе»        (in_progress, default)   — отчёт создан, заполняется
    - «На утверждении»  (pending_approval)       — отчёт отправлен на проверку
    - «Утверждён»       (approved)               — финальный, вход в KPI
    - «Отклонён»        (rejected)               — возврат в работу

Report.status_id пока указывает на spec_statuss — переключение FK в
отдельной миграции (после того как модель Spec_Report_Status появится).

Revision ID: f3a4b5c6d7e8
Revises: e2b3c4d5f6a7
Create Date: 2026-09-05
"""
from alembic import op
import sqlalchemy as sa


revision = 'f3a4b5c6d7e8'
down_revision = 'e2b3c4d5f6a7'
branch_labels = None
depends_on = None


# (name, is_default) — в канон-виде без code
SPEC_REPORT_STATUSES = [
    ('В работе',       True),
    ('На утверждении', False),
    ('Утверждён',      False),
    ('Отклонён',       False),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS spec_report_statuses (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR NOT NULL UNIQUE,
            is_default  BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            description VARCHAR
        )
        """
    )

    # Partial unique — ровно одна is_default = true.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_spec_report_statuses_is_default_true "
        "ON spec_report_statuses (is_default) WHERE is_default = true"
    )

    conn = op.get_bind()
    for name, is_default in SPEC_REPORT_STATUSES:
        conn.execute(
            sa.text(
                "INSERT INTO spec_report_statuses (name, is_default) "
                "VALUES (:name, :is_default) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name, "is_default": is_default},
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_spec_report_statuses_is_default_true")
    op.execute("DROP TABLE IF EXISTS spec_report_statuses")
