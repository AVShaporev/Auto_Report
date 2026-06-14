"""autogen orders: foundation (spec_orders flags + periods code + orders period_start_date + system user)

Подготавливает фичу «авто-генерация заявок» (см. service/order_autogen.py).
Одной миграцией:

1) `spec_orders`:
   - is_default_planned BOOL DEFAULT false
   - is_default_primary BOOL DEFAULT false
   - partial UNIQUE-индексы (только одна строка с TRUE для каждого флага)
   - сидируем существующие code='planned' → is_default_planned=TRUE,
     code='primary' → is_default_primary=TRUE.

2) `periods`:
   - code VARCHAR(20) NULL — календарный код расписания
     (monthly/quarterly/semiannual/yearly/custom). Старые периоды
     получают NULL → авто-tick их игнорирует.

3) `orders`:
   - number расширяется до VARCHAR(200) — новый формат номера длинный.
   - period_start_date DATE NULL — дата начала периода обслуживания.
   - partial UNIQUE(object_id, spec_order_id, period_start_date) WHERE
     period_start_date IS NOT NULL — защита от дублей при tick'ах.

4) Системный пользователь для авто-заявок (Order.user_id NOT NULL):
   - роль `Система` (is_protected=TRUE, минимальные права);
   - юзер `system` (is_protected=TRUE, is_active=FALSE, пароль не задан —
     логин невозможен).
   - hashed_password = bcrypt-плейсхолдер длиной 60 (валидный по схеме,
     но не совпадает ни с каким реальным паролем — passlib.verify вернёт
     False для любого ввода).

Идемпотентность: все INSERT'ы под `ON CONFLICT DO NOTHING`, UPDATE-ы
по фильтру `WHERE NOT exists / WHERE code = ...` — повторный накат
не падает.

Revision ID: e7c2a5d1f3b8
Revises: d4f8e3c7b2a1
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa


revision = 'e7c2a5d1f3b8'
down_revision = 'd4f8e3c7b2a1'
branch_labels = None
depends_on = None


# Пароль системного пользователя: bcrypt-валидный плейсхолдер, который
# не совпадает ни с одним реальным паролем (хеш сгенерирован для
# случайной 64-байтной строки, потом стёрт). passlib.verify вернёт False
# для любого пользовательского ввода → логин под `system` невозможен.
_SYSTEM_USER_PASSWORD_HASH = (
    "$2b$12$Wd0XSeYJlDH9p1cZ7eYxR.uYpZGfQ4xK4ZCnWQK1B4eEC9mLcKvFa"
)


def upgrade() -> None:
    # ====== 1. spec_orders: флаги is_default_planned / is_default_primary ======
    op.add_column(
        'spec_orders',
        sa.Column(
            'is_default_planned',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'spec_orders',
        sa.Column(
            'is_default_primary',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )

    # Partial UNIQUE: в таблице может быть максимум одна строка с TRUE
    # на каждый флаг (на FALSE — без ограничения).
    op.create_index(
        'uq_spec_orders_one_default_planned',
        'spec_orders',
        ['is_default_planned'],
        unique=True,
        postgresql_where=sa.text('is_default_planned = TRUE'),
    )
    op.create_index(
        'uq_spec_orders_one_default_primary',
        'spec_orders',
        ['is_default_primary'],
        unique=True,
        postgresql_where=sa.text('is_default_primary = TRUE'),
    )

    conn = op.get_bind()

    # Сидируем флаги на существующих системных типах.
    conn.execute(sa.text(
        "UPDATE spec_orders SET is_default_planned = TRUE WHERE code = 'planned'"
    ))
    conn.execute(sa.text(
        "UPDATE spec_orders SET is_default_primary = TRUE WHERE code = 'primary'"
    ))

    # ====== 2. periods: code ======
    op.add_column(
        'periods',
        sa.Column('code', sa.String(length=20), nullable=True),
    )
    op.create_check_constraint(
        'ck_periods_code_valid',
        'periods',
        "code IS NULL OR code IN ('monthly', 'quarterly', 'semiannual', 'yearly', 'custom')",
    )

    # ====== 3. orders: number → 200, period_start_date ======
    op.alter_column(
        'orders',
        'number',
        existing_type=sa.String(),
        type_=sa.String(length=200),
        existing_nullable=False,
    )
    op.add_column(
        'orders',
        sa.Column('period_start_date', sa.Date(), nullable=True),
    )
    op.create_index(
        'uq_orders_object_specorder_periodstart',
        'orders',
        ['object_id', 'spec_order_id', 'period_start_date'],
        unique=True,
        postgresql_where=sa.text('period_start_date IS NOT NULL'),
    )

    # ====== 4. system role + user ======
    # Создаём роль `Система` с минимальными правами. В model.Role ~130
    # boolean-колонок (все права), у большинства только client-side `default=False`
    # без server_default → raw INSERT нужно либо перечислить их все, либо
    # задать дефолты динамически. Рефлексируем таблицу, ставим все BOOLEAN-колонки
    # с NULL-дефолтом в FALSE, кроме is_protected (TRUE).
    roles_t = sa.Table('roles', sa.MetaData(), autoload_with=conn)
    bool_cols = [
        c.name for c in roles_t.columns
        if isinstance(c.type, sa.Boolean) and not c.server_default
    ]
    role_values: dict = {col: False for col in bool_cols}
    role_values["is_protected"] = True

    # Динамический INSERT с FALSE на все права + TRUE на is_protected.
    cols_sql = ", ".join(["name", "description", "created_at", "updated_at"] + list(role_values.keys()))
    placeholders = ", ".join([
        ":name", ":description", "NOW()", "NOW()",
        *[f":{col}" for col in role_values.keys()],
    ])
    insert_role_sql = (
        f"INSERT INTO roles ({cols_sql}) VALUES ({placeholders}) "
        "ON CONFLICT (name) DO NOTHING"
    )
    conn.execute(sa.text(insert_role_sql), {
        "name": "Система",
        "description": "Системная роль для авто-генерации заявок. Не назначайте людям.",
        **role_values,
    })

    # Юзер `system`: is_active=FALSE → не считается «живым»; пароль —
    # bcrypt-плейсхолдер, логин невозможен. Поле «hash» (так оно реально
    # называется в model.user.User, не hashed_password).
    conn.execute(sa.text(
        """
        INSERT INTO users (name, full_name, hash, is_active, is_protected,
                           role_id, created_at, updated_at)
        SELECT 'system',
               'Системный пользователь',
               :pwhash,
               FALSE, TRUE,
               r.id,
               NOW(), NOW()
        FROM roles r
        WHERE r.name = 'Система'
          AND NOT EXISTS (SELECT 1 FROM users u WHERE u.name = 'system')
        """
    ), {"pwhash": _SYSTEM_USER_PASSWORD_HASH})

    # На таблице users большинство boolean-полей уже имеют server_default,
    # но если в проде встретится NOT NULL без default — добьём явным UPDATE
    # (no-op в нашей дев-схеме, защита от чудес в проде).
    conn.execute(sa.text(
        "UPDATE users SET is_active = COALESCE(is_active, FALSE), "
        "is_protected = COALESCE(is_protected, TRUE) "
        "WHERE name = 'system'"
    ))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DELETE FROM users WHERE name = 'system'"))
    conn.execute(sa.text("DELETE FROM roles WHERE name = 'Система'"))

    op.drop_index('uq_orders_object_specorder_periodstart', table_name='orders')
    op.drop_column('orders', 'period_start_date')
    op.alter_column(
        'orders',
        'number',
        existing_type=sa.String(length=200),
        type_=sa.String(),
        existing_nullable=False,
    )

    op.drop_constraint('ck_periods_code_valid', 'periods', type_='check')
    op.drop_column('periods', 'code')

    op.drop_index('uq_spec_orders_one_default_primary', table_name='spec_orders')
    op.drop_index('uq_spec_orders_one_default_planned', table_name='spec_orders')
    op.drop_column('spec_orders', 'is_default_primary')
    op.drop_column('spec_orders', 'is_default_planned')
