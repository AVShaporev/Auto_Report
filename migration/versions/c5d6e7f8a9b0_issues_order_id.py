"""issues.order_id — заявка на устранение неисправности

Менеджер создаёт из карточки неисправности заявку на её устранение (часто
позже, когда появился ЗИП). Связь 1 неисправность → 1 заявка храним на
стороне неисправности: nullable FK на orders.id.

ON DELETE SET NULL — удаление заявки не должно удалять неисправность,
она просто снова становится «без заявки» и из неё можно создать новую.

Revision ID: c5d6e7f8a9b0
Revises: b4d5e6f7a8c9
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa


revision = 'c5d6e7f8a9b0'
down_revision = 'b4d5e6f7a8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'issues',
        sa.Column(
            'order_id',
            sa.Integer(),
            nullable=True,
            comment='ID заявки на устранение',
        ),
    )
    op.create_foreign_key(
        'fk_issues_order_id_orders',
        'issues', 'orders',
        ['order_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_issues_order_id', 'issues', ['order_id'])


def downgrade() -> None:
    op.drop_index('ix_issues_order_id', table_name='issues')
    op.drop_constraint('fk_issues_order_id_orders', 'issues', type_='foreignkey')
    op.drop_column('issues', 'order_id')
