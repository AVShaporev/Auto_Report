"""add spec_journals + seed maintenance journal + role permissions

Создаёт справочник «Виды журналов» (`spec_journals`):
  - name (UNIQUE), short_name, code (UNIQUE NULLABLE), is_system,
    description, template_filename, template_storage_path
  - сидим 1 системный тип `maintenance` (Журнал технического обслуживания)
    с привязкой к seed-шаблону `templates/maintenance.docx`.

Добавляет 4 boolean-колонки прав на `roles`:
  spec_journal_read / spec_journal_create / spec_journal_modify / spec_journal_delete.

Семантика NULL+UNIQUE в `code`: пользовательские журналы могут не иметь
машинного кода (Postgres допускает несколько NULL в UNIQUE-колонке).

ВАЖНО: миграция только прописывает PATH шаблона в БД. Сам файл
кладёт scripts/seed_templates.py (см. Phase 3 шаблонов).

Revision ID: b8e2f4a6d5c3
Revises: a7f9d3e2c8b1
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa


revision = 'b8e2f4a6d5c3'
down_revision = 'a7f9d3e2c8b1'
branch_labels = None
depends_on = None


SYSTEM_JOURNALS = [
    # (name, short_name, code, description, template_filename, template_storage_path)
    (
        'Журнал технического обслуживания',
        'Журнал ТО',
        'maintenance',
        'Системный тип журнала: журнал технического обслуживания систем',
        'Jurnal_TO.docx',
        'templates/maintenance.docx',
    ),
]


def upgrade() -> None:
    # 1. Таблица spec_journals.
    op.create_table(
        'spec_journals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('short_name', sa.String(), nullable=True),
        sa.Column('code', sa.String(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('template_filename', sa.String(), nullable=True),
        sa.Column('template_storage_path', sa.String(), nullable=True),
        sa.UniqueConstraint('name', name='uq_spec_journals_name'),
        sa.UniqueConstraint('code', name='uq_spec_journals_code'),
    )

    # 2. Права на роли.
    op.add_column('roles', sa.Column('spec_journal_read',   sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('roles', sa.Column('spec_journal_create', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('roles', sa.Column('spec_journal_modify', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('roles', sa.Column('spec_journal_delete', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    conn = op.get_bind()

    # 3. Сидим системные журналы (INSERT, ON CONFLICT DO NOTHING).
    for name, short_name, code, description, fn, sp in SYSTEM_JOURNALS:
        conn.execute(
            sa.text(
                """
                INSERT INTO spec_journals
                    (name, short_name, code, is_system, description,
                     template_filename, template_storage_path)
                VALUES (:name, :short, :code, TRUE, :descr, :fn, :sp)
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "name": name, "short": short_name, "code": code,
                "descr": description, "fn": fn, "sp": sp,
            },
        )

        # Промоут существующих user-строк по name → докатываем code/is_system/template
        # WHERE-condition защищает от перетирания, если юзер уже поставил
        # свой code в этой строке.
        conn.execute(
            sa.text(
                """
                UPDATE spec_journals
                SET code = :code, is_system = TRUE,
                    description = COALESCE(description, :descr),
                    template_filename = COALESCE(template_filename, :fn),
                    template_storage_path = COALESCE(template_storage_path, :sp)
                WHERE name = :name AND (code IS NULL OR code = :code)
                """
            ),
            {
                "name": name, "code": code, "descr": description,
                "fn": fn, "sp": sp,
            },
        )

    # 4. Включаем все 4 spec_journal_* для админских ролей.
    conn.execute(
        sa.text(
            """
            UPDATE roles
            SET spec_journal_read   = TRUE,
                spec_journal_create = TRUE,
                spec_journal_modify = TRUE,
                spec_journal_delete = TRUE
            WHERE is_admin = TRUE OR is_superadmin = TRUE
            """
        )
    )


def downgrade() -> None:
    op.drop_column('roles', 'spec_journal_delete')
    op.drop_column('roles', 'spec_journal_modify')
    op.drop_column('roles', 'spec_journal_create')
    op.drop_column('roles', 'spec_journal_read')
    op.drop_table('spec_journals')
