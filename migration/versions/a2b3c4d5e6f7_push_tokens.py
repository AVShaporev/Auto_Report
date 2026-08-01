"""push_tokens table for FCM/APNs registration (Mobile M1.2)

Инфраструктура для будущего sending'а push-уведомлений с backend'а
на mobile-клиента (M7 в mobile-roadmap). Пока таблица + endpoints
регистрации — сами уведомления не шлём.

Модель:
  - token уникален глобально (FCM registration token и APNs device
    token — это device-scope, а не user-scope). При смене юзера на
    том же устройстве register-эндпоинт делает upsert user_id.
  - platform: 'ios' | 'android' | 'web' (для будущего web-push через VAPID).
  - device_id — клиентский идентификатор для UI «мои устройства».
  - is_active — soft-disable после серии send-failures (запишем в M7,
    сейчас всегда TRUE).
  - last_seen_at — обновляется на register/refresh, по нему cleanup-cron
    сносит токены старше 30 дней.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa


revision = 'a2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'push_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('platform', sa.String(length=16), nullable=False),
        sa.Column('token', sa.String(length=512), nullable=False),
        sa.Column('device_id', sa.String(length=128), nullable=True),
        sa.Column('app_version', sa.String(length=32), nullable=True),
        sa.Column(
            'last_seen_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'is_active', sa.Boolean(),
            server_default=sa.text('true'), nullable=False,
        ),
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
    op.create_check_constraint(
        'ck_push_tokens_platform',
        'push_tokens',
        "platform IN ('ios', 'android', 'web')",
    )
    op.create_unique_constraint(
        'uq_push_tokens_token', 'push_tokens', ['token']
    )
    op.create_index(
        'ix_push_tokens_user_active',
        'push_tokens',
        ['user_id', 'is_active'],
    )
    op.create_index(
        'ix_push_tokens_last_seen',
        'push_tokens',
        ['last_seen_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_push_tokens_last_seen', table_name='push_tokens')
    op.drop_index('ix_push_tokens_user_active', table_name='push_tokens')
    op.drop_constraint('uq_push_tokens_token', 'push_tokens', type_='unique')
    op.drop_constraint('ck_push_tokens_platform', 'push_tokens', type_='check')
    op.drop_table('push_tokens')
