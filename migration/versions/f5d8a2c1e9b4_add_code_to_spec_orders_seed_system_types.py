"""add code to spec_orders + seed system order types

Добавляет NULLABLE UNIQUE колонку `code` в spec_orders и идемпотентно
сидит 4 системных типа заявок: emergency, primary, planned, test.

Семантика NULL+UNIQUE: пользовательские типы заявок могут не иметь
машинного кода (Postgres допускает несколько NULL в UNIQUE-колонке),
а системные имеют стабильный код для обращения из бизнес-логики и
будущей привязки шаблонов документов.

Идемпотентность:
  1. INSERT ... ON CONFLICT DO NOTHING — если строки с такими name
     уже заведены пользователем, пропускаем.
  2. UPDATE WHERE name = ... AND (code IS NULL OR code = ...) —
     докатываем code + is_system на существующие строки. Защита от
     перетирания: если пользователь уже руками поставил другой code,
     не трогаем.

Revision ID: f5d8a2c1e9b4
Revises: c3a7f2b9e814
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa


revision = 'f5d8a2c1e9b4'
down_revision = 'c3a7f2b9e814'
branch_labels = None
depends_on = None


SYSTEM_TYPES = [
    # (name, short_name, code, description)
    ('Аварийная', 'АВАР', 'emergency', 'Системный тип заявки: аварийный вызов'),
    ('Первичная', 'ПЕРВ', 'primary', 'Системный тип заявки: первичный осмотр / обследование'),
    ('Плановая ТО', 'ТО', 'planned', 'Системный тип заявки: плановое техническое обслуживание'),
    ('Испытания', 'ИСП', 'test', 'Системный тип заявки: испытания / проверка работоспособности'),
]


def upgrade() -> None:
    # 1. Добавляем NULLABLE UNIQUE колонку `code`.
    op.add_column(
        'spec_orders',
        sa.Column('code', sa.String(), nullable=True),
    )
    op.create_unique_constraint(
        'uq_spec_orders_code',
        'spec_orders',
        ['code'],
    )

    conn = op.get_bind()

    # 2. Сидим системные типы заявок (INSERT, ON CONFLICT DO NOTHING).
    conn.execute(sa.text(
        """
        INSERT INTO spec_orders (name, short_name, code, is_system, description) VALUES
            ('Аварийная',   'АВАР', 'emergency', TRUE, 'Системный тип заявки: аварийный вызов'),
            ('Первичная',   'ПЕРВ', 'primary',   TRUE, 'Системный тип заявки: первичный осмотр / обследование'),
            ('Плановая ТО', 'ТО',   'planned',   TRUE, 'Системный тип заявки: плановое техническое обслуживание'),
            ('Испытания',   'ИСП',  'test',      TRUE, 'Системный тип заявки: испытания / проверка работоспособности')
        ON CONFLICT DO NOTHING
        """
    ))

    # 3. Промоут существующих user-строк по name → docатываем code + is_system.
    #    WHERE-condition защищает от перетирания, если юзер уже поставил
    #    свой code в этой строке.
    for name, _short, code, _desc in SYSTEM_TYPES:
        conn.execute(
            sa.text(
                """
                UPDATE spec_orders
                SET code = :code, is_system = TRUE
                WHERE name = :name AND (code IS NULL OR code = :code)
                """
            ),
            {"name": name, "code": code},
        )


def downgrade() -> None:
    op.drop_constraint('uq_spec_orders_code', 'spec_orders', type_='unique')
    op.drop_column('spec_orders', 'code')
