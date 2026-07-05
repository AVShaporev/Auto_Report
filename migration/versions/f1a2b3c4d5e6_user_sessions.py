"""user_sessions table for refresh-token rotation

Для перехода с stateless refresh-token'а на rotating stateful. Каждый
успешный /login и /refresh создаёт запись; /refresh валидирует jti по
БД и rotate'ит (старая помечается revoked_at, выпускается новая).
Позволяет:
  - разлогинить конкретное устройство (revoke сессии по id);
  - разлогинить юзера везде (revoke-all-sessions);
  - показать список активных сессий в UI «Мои сессии».

Web-легаси: если refresh пришёл БЕЗ записи в user_sessions (старые токены,
выпущенные до этой миграции), сервис допускает fallback без ротации —
такой токен продолжит работать до истечения. Новые логины уже пишут
сессию.

Revision ID: f1a2b3c4d5e6
Revises: a9c7e2b4f6d8
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa


revision = 'f1a2b3c4d5e6'
down_revision = 'a9c7e2b4f6d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('refresh_jti', sa.String(length=64), nullable=False),
        sa.Column('device_info', sa.JSON(), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('geo_country', sa.String(length=8), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column('description', sa.String(), nullable=True),
    )
    op.create_unique_constraint(
        'uq_user_sessions_refresh_jti', 'user_sessions', ['refresh_jti']
    )
    op.create_index(
        'ix_user_sessions_user_active',
        'user_sessions',
        ['user_id', 'revoked_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_user_sessions_user_active', table_name='user_sessions')
    op.drop_constraint('uq_user_sessions_refresh_jti', 'user_sessions', type_='unique')
    op.drop_table('user_sessions')
