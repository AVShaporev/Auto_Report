"""add is_system to spec_* catalogs + seed status/priority

Добавляет колонку `is_system` (BOOLEAN NOT NULL DEFAULT FALSE) во все 13
spec_* таблиц-справочников. Затем идемпотентно сидит системные строки в
spec_statuss (6 кодов) и spec_prioritys (4 кода) — те, что захардкожены
в бизнес-логике (см. service/issue.py, service/report.py, IssueForm.vue).

Идемпотентность: INSERT ... ON CONFLICT DO NOTHING; затем UPDATE по
известным code'ам ставит is_system=TRUE. Это покрывает кейс «юзер уже
сам завёл строку с этим code или name» — миграция не упадёт и просто
промаркирует существующую строку как системную, не трогая её name/
description.

Revision ID: c3a7f2b9e814
Revises: a1b2c3d4e5f6
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3a7f2b9e814'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


SPEC_TABLES = [
    'spec_arials',
    'spec_builds',
    'spec_contracts',
    'spec_equipments',
    'spec_job_titles',
    'spec_localitys',
    'spec_orders',
    'spec_prioritys',
    'spec_regions',
    'spec_rooms',
    'spec_statuss',
    'spec_streets',
    'spec_systems',
]


def upgrade() -> None:
    # 1. Добавляем колонку is_system во все 13 spec_* таблиц.
    for table in SPEC_TABLES:
        op.add_column(
            table,
            sa.Column(
                'is_system',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('false'),
            ),
        )

    conn = op.get_bind()

    # 2. Сидим системные статусы (используются в issue + report workflow).
    conn.execute(sa.text(
        """
        INSERT INTO spec_statuss (name, code, is_system, description) VALUES
            ('Новая', 'new', TRUE, 'Системный статус: дефолт для новой неисправности'),
            ('В работе', 'in_progress', TRUE, 'Системный статус: неисправность в обработке'),
            ('Исправлена', 'resolved', TRUE, 'Системный статус: триггерит требование resolved_date'),
            ('Закрыта', 'closed', TRUE, 'Системный статус: финальный, считается устранённым'),
            ('Не утверждён', 'not_approved', TRUE, 'Системный статус: дефолт для нового отчёта'),
            ('Утверждён', 'approved', TRUE, 'Системный статус: отчёт согласован, аттач-гейт открыт')
        ON CONFLICT DO NOTHING
        """
    ))
    conn.execute(sa.text(
        """
        UPDATE spec_statuss SET is_system = TRUE
        WHERE code IN ('new', 'in_progress', 'resolved', 'closed', 'not_approved', 'approved')
        """
    ))

    # 3. Сидим системные приоритеты (используются в IssueForm дефолте + CSS-классах).
    conn.execute(sa.text(
        """
        INSERT INTO spec_prioritys (name, code, is_system, description) VALUES
            ('Низкий', 'low', TRUE, 'Системный приоритет'),
            ('Средний', 'medium', TRUE, 'Системный приоритет (дефолт новой неисправности)'),
            ('Высокий', 'high', TRUE, 'Системный приоритет'),
            ('Критический', 'critical', TRUE, 'Системный приоритет')
        ON CONFLICT DO NOTHING
        """
    ))
    conn.execute(sa.text(
        """
        UPDATE spec_prioritys SET is_system = TRUE
        WHERE code IN ('low', 'medium', 'high', 'critical')
        """
    ))


def downgrade() -> None:
    # Колонку дропаем; сидированные строки остаются (на них могут уже
    # ссылаться issues/reports — FK constraint не даст их безопасно удалить).
    for table in reversed(SPEC_TABLES):
        op.drop_column(table, 'is_system')
