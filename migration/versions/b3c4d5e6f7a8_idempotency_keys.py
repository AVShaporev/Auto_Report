"""idempotency_keys table for Mobile M1.4

Mobile-клиент в поле теряет связь на середине POST/PUT/PATCH и ретаит
запрос — backend без idempotency создаёт дубли (две одинаковые заявки,
два отчёта). Middleware проверяет `X-Idempotency-Key` заголовок и
короткое время кэширует успешные ответы, так что повторный запрос
с тем же ключом возвращает тот же ответ без повторного выполнения
логики.

Uniq (user_name, key) — ключ scope'ится по юзеру, чтобы юзер A не мог
подсмотреть закэшированный ответ юзера B.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-08-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'idempotency_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        # user_name (не user_id): JWT содержит sub = User.name.
        # Резолвить в id прямо в middleware — лишний SELECT.
        sa.Column('user_name', sa.String(length=50), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('path', sa.String(length=512), nullable=False),
        sa.Column('status_code', sa.SmallInteger(), nullable=False),
        # response_body — bytes (JSON или другой content-type) в bytea.
        # JSONB не подходит — endpoint может вернуть XML/DOCX/бинарь.
        sa.Column('response_body', sa.LargeBinary(), nullable=False),
        # response_headers сохраняем как JSONB {'content-type': '...', ...},
        # чтобы восстановить Content-Type, Content-Disposition и т.п.
        sa.Column('response_headers', JSONB(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        'uq_idempotency_keys_user_key',
        'idempotency_keys',
        ['user_name', 'key'],
    )
    op.create_index(
        'ix_idempotency_keys_expires_at',
        'idempotency_keys',
        ['expires_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_idempotency_keys_expires_at', table_name='idempotency_keys')
    op.drop_constraint(
        'uq_idempotency_keys_user_key', 'idempotency_keys', type_='unique'
    )
    op.drop_table('idempotency_keys')
