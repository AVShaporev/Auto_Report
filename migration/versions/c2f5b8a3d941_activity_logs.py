"""activity_logs: пользовательские действия (v1.0.14, task #312)

Новая таблица для журнала пользовательских действий (Кто/Когда/Что):
create/update/delete/change_status по ключевым сущностям + login/logout.
Заменит текущий «Логи» в UI тенанта (там были HTTP-логи, шумные и
неструктурированные). Технические логи (JSONL) переезжают в admin.cool-doc.ru
отдельной фазой.

Схема:
  id            SERIAL PK
  user_id       INTEGER NULL  → users.id ON DELETE SET NULL
  user_name     VARCHAR(255)  — снапшот имени на момент действия
                (сохраняется даже после удаления юзера)
  action        VARCHAR(50)   — 'create' | 'update' | 'delete' |
                                'change_status' | 'login' | 'logout' | ...
  entity        VARCHAR(50)   — 'order' | 'report' | 'issue' | 'user' | ...
  entity_id     INTEGER NULL  — id сущности (для delete может быть NULL если
                                уже потеряли)
  summary       VARCHAR(500)  — человекочитаемый русский текст,
                                напр. «Создал заявку №2026-001»
  details       JSONB NULL    — доп. данные (before/after diff, params)
  created_at    TIMESTAMP     — server_default now()

Индексы:
  - created_at DESC (частый ORDER BY)
  - user_id (фильтр по юзеру)
  - entity (фильтр по типу)

Revision ID: c2f5b8a3d941
Revises: b1c2d3e4f5a6
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "c2f5b8a3d941"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_name", sa.String(255), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activity_logs_created_at", "activity_logs",
                    ["created_at"], unique=False, postgresql_ops={"created_at": "DESC"})
    op.create_index("ix_activity_logs_user_id", "activity_logs",
                    ["user_id"], unique=False)
    op.create_index("ix_activity_logs_entity", "activity_logs",
                    ["entity"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activity_logs_entity", table_name="activity_logs")
    op.drop_index("ix_activity_logs_user_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_created_at", table_name="activity_logs")
    op.drop_table("activity_logs")
