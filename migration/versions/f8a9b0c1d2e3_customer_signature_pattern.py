"""Подпись заказчика узором (ПЭП) вместо картинки-росчерка

- objects.requires_signature — «подтверждение выполнения работ подписью
  ответственного», по умолчанию false;
- customer_representatives — представители заказчика на объекте: ФИО,
  должность, контакты, bcrypt-хеш узора 4×4, счётчик ошибок и блокировка,
  одноразовая ссылка для задания узора (хранится sha256);
- app_keys — ключи организации (RSA для офлайн-подписи: телефон шифрует узор
  открытым ключом, сервер проверяет при синхронизации);
- reports: картинка-росчерк (signature_path, e7f8a9b0c1d2 — была только на
  stage) убрана; добавлены representative_id, signature_status
  (verified | failed), signature_code (код проверки подписи).

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-09-19
"""
from alembic import op
import sqlalchemy as sa


revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def _base_cols():
    return [
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
    ]


def upgrade() -> None:
    op.add_column("objects", sa.Column(
        "requires_signature", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "customer_representatives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("object_id", sa.Integer(), sa.ForeignKey("objects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("position", sa.String(length=150), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("pattern_hash", sa.String(length=200), nullable=True),
        sa.Column("pattern_set_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enroll_token_hash", sa.String(length=64), nullable=True),
        sa.Column("enroll_expires_at", sa.DateTime(timezone=True), nullable=True),
        *_base_cols(),
    )
    op.create_index("ix_customer_representatives_object_id", "customer_representatives", ["object_id"])
    op.create_index("ix_customer_representatives_enroll_token_hash", "customer_representatives",
                    ["enroll_token_hash"], unique=True)

    op.create_table(
        "app_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False, unique=True),
        sa.Column("private_pem", sa.Text(), nullable=False),
        sa.Column("public_pem", sa.Text(), nullable=False),
        *_base_cols(),
    )

    op.drop_column("reports", "signature_path")
    op.add_column("reports", sa.Column(
        "representative_id", sa.Integer(),
        sa.ForeignKey("customer_representatives.id", ondelete="SET NULL"), nullable=True))
    op.add_column("reports", sa.Column("signature_status", sa.String(length=16), nullable=True))
    op.add_column("reports", sa.Column("signature_code", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "signature_code")
    op.drop_column("reports", "signature_status")
    op.drop_column("reports", "representative_id")
    op.add_column("reports", sa.Column("signature_path", sa.String(length=500), nullable=True))
    op.drop_table("app_keys")
    op.drop_index("ix_customer_representatives_enroll_token_hash", table_name="customer_representatives")
    op.drop_index("ix_customer_representatives_object_id", table_name="customer_representatives")
    op.drop_table("customer_representatives")
    op.drop_column("objects", "requires_signature")
