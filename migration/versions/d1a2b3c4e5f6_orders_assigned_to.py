"""orders.assigned_to_id — ответственный (nullable FK на users)

Revision ID: d1a2b3c4e5f6
Revises: c8a4d3e2f9b7
Create Date: 2026-08-27

Ранее у заявки был только user_id (АВТОР создания). Добавляем отдельное
поле assigned_to_id — ответственного за исполнение. В mobile "Мои" будет
фильтровать по assigned_to_id (сейчас фильтр стоит на user_id — это баг
для инженеров, которые заявки не создают, а получают).

Backfill: NULL для всех существующих. Проставят вручную через web-UI.
"""
from alembic import op
import sqlalchemy as sa


revision = "d1a2b3c4e5f6"
down_revision = "c8a4d3e2f9b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("assigned_to_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_orders_assigned_to_id_users",
        "orders",
        "users",
        ["assigned_to_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_orders_assigned_to_id",
        "orders",
        ["assigned_to_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_assigned_to_id", table_name="orders")
    op.drop_constraint("fk_orders_assigned_to_id_users", "orders", type_="foreignkey")
    op.drop_column("orders", "assigned_to_id")
