"""media_upload_sessions table for Mobile M1.5 chunked upload

Mobile-инженер в поле снимает 5-10 фото по 3-5 MB каждое, слабый LTE.
Обычный multipart POST умирает на 30% на flaky-соединении.

Chunked upload через session:
  1. POST /api/mobile/media/upload/init → создаётся row + tmp-файл.
  2. PUT /api/mobile/media/upload/{upload_id} с Content-Range: bytes X-Y/TOTAL
     — append chunk. Клиент может ретрайить с того же offset при разрыве.
  3. При received==total → сервер finalize'ит: resize через Pillow
     (JPEG q=80 max 2000px), move в /app/media/mobile/, is_complete=True.

Session-based (не TUS-совместимо) — internal-app, TUS overkill.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-08-02
"""
from alembic import op
import sqlalchemy as sa


revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'media_upload_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('upload_id', sa.String(length=64), nullable=False),
        sa.Column('user_name', sa.String(length=50), nullable=False),
        # kind — семантика назначения: 'issue_photo', 'report_signature',
        # 'report_photo', 'avatar'. Пока строкой, чтобы не связываться с
        # enum-миграциями.
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('filename', sa.String(length=256), nullable=False),
        sa.Column('total_size', sa.BigInteger(), nullable=False),
        sa.Column(
            'received_bytes', sa.BigInteger(),
            nullable=False, server_default='0',
        ),
        sa.Column('tmp_path', sa.String(length=512), nullable=False),
        sa.Column('final_path', sa.String(length=512), nullable=True),
        sa.Column(
            'is_complete', sa.Boolean(),
            nullable=False, server_default=sa.text('false'),
        ),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        'uq_media_upload_sessions_upload_id',
        'media_upload_sessions',
        ['upload_id'],
    )
    op.create_index(
        'ix_media_upload_sessions_expires',
        'media_upload_sessions',
        ['expires_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_media_upload_sessions_expires', table_name='media_upload_sessions')
    op.drop_constraint(
        'uq_media_upload_sessions_upload_id',
        'media_upload_sessions', type_='unique',
    )
    op.drop_table('media_upload_sessions')
