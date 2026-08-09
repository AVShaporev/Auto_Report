"""media_upload_sessions: добавить Base-колонку description

Миграция c4d5e6f7a8b9 создала таблицу с created_at + updated_at, но
пропустила description (тоже наследуется от Base через str_description).
INSERT падает с UndefinedColumnError на первом же POST /api/mobile/
media/upload/init от мобильного клиента (M5.3 photo upload).

Тот же баг что мы фиксили вчера для idempotency_keys миграцией
c5e6f7a8b9c0 — паттерн повторился на соседней таблице M1.5.

Revision ID: d7f8a9b0c1e2
Revises: c5e6f7a8b9c0
Create Date: 2026-08-09
"""
from alembic import op
import sqlalchemy as sa


revision = 'd7f8a9b0c1e2'
down_revision = 'c5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS: hi-tech БД уже могла получить эту колонку через ручной
    # ALTER TABLE (был quick-fix пока GHA не докатил образ с миграцией).
    # Не мешаем повторному прогону, чтобы alembic upgrade не упал на дубле.
    op.execute(
        "ALTER TABLE media_upload_sessions "
        "ADD COLUMN IF NOT EXISTS description VARCHAR"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE media_upload_sessions DROP COLUMN IF EXISTS description"
    )
