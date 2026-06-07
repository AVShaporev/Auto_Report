"""add template fields to spec_orders + bind seed templates

Добавляет 2 NULLABLE колонки в spec_orders:
  - template_filename       — оригинальное имя файла, как загрузил админ
                              (показывается в UI: «Текущий: Акт дефекта.docx»)
  - template_storage_path   — путь относительно MEDIA_PATH (см. config.py),
                              где реально лежит файл на диске сервера

Связывает 3 из 4 системных типов заявок с seed-шаблонами (test остаётся без
шаблона — админ зальёт через UI позже, когда дойдёт):
  - emergency → 'Акт дефекта.docx'
  - primary   → 'Act of primary examination.dotx'
  - planned   → 'Monthly maintenance act.dotx'

ВАЖНО: миграция только прописывает PATH'ы в БД. Сами файлы кладёт в storage
deploy-скрипт (cp -n из templates/seeds/). До копирования render будет
отдавать 404 «template file missing — admin needs to upload».

Revision ID: a7f9d3e2c8b1
Revises: f5d8a2c1e9b4
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7f9d3e2c8b1'
down_revision = 'f5d8a2c1e9b4'
branch_labels = None
depends_on = None


SEED_BINDINGS = [
    # (spec_order.code, original filename, storage path relative to MEDIA_PATH)
    ('emergency', 'Акт дефекта.docx',                'templates/emergency.docx'),
    ('primary',   'Act of primary examination.dotx', 'templates/primary.dotx'),
    ('planned',   'Monthly maintenance act.dotx',    'templates/planned.dotx'),
]


def upgrade() -> None:
    op.add_column(
        'spec_orders',
        sa.Column('template_filename', sa.String(), nullable=True),
    )
    op.add_column(
        'spec_orders',
        sa.Column('template_storage_path', sa.String(), nullable=True),
    )

    conn = op.get_bind()

    # Прописываем seed-привязки. WHERE-condition защищает от перезаписи,
    # если админ уже руками загрузил свой шаблон до этого деплоя.
    for code, filename, storage_path in SEED_BINDINGS:
        conn.execute(
            sa.text(
                """
                UPDATE spec_orders
                SET template_filename = :fn, template_storage_path = :sp
                WHERE code = :code
                  AND template_filename IS NULL
                  AND template_storage_path IS NULL
                """
            ),
            {"code": code, "fn": filename, "sp": storage_path},
        )


def downgrade() -> None:
    op.drop_column('spec_orders', 'template_storage_path')
    op.drop_column('spec_orders', 'template_filename')
