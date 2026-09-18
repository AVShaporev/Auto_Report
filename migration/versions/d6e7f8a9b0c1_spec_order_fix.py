"""seed системного типа заявки «Устранение неисправности» (code=fix)

Заявка на устранение создаётся из карточки неисправности (1.0.61). Раньше
менеджер выбирал тип вручную, обычно «Аварийная» — номер получался
`…/АВАР/N`, а SLA аварийного типа сразу красил заявку как просроченную.

Отдельный системный тип: short_name «РЕМ», sla_kind='manual' (срок ставит
менеджер — ЗИП на руках, но сроки у всех разные).

Идемпотентно, как f5d8a2c1e9b4:
  1. INSERT ... ON CONFLICT DO NOTHING — если name или code уже заняты,
     пропускаем.
  2. UPDATE по name — промоутим пользовательскую строку с таким именем
     (code + is_system), если code у неё пустой.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa


revision = 'd6e7f8a9b0c1'
down_revision = 'c5d6e7f8a9b0'
branch_labels = None
depends_on = None


NAME = 'Устранение неисправности'
CODE = 'fix'


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        """
        INSERT INTO spec_orders (name, short_name, code, is_system, sla_kind, description)
        VALUES (:name, 'РЕМ', :code, TRUE, 'manual',
                'Системный тип заявки: устранение неисправности (создаётся из карточки неисправности)')
        ON CONFLICT DO NOTHING
        """
    ), {"name": NAME, "code": CODE})
    conn.execute(sa.text(
        """
        UPDATE spec_orders
        SET code = :code, is_system = TRUE
        WHERE name = :name AND (code IS NULL OR code = :code)
          AND NOT EXISTS (SELECT 1 FROM spec_orders WHERE code = :code AND name <> :name)
        """
    ), {"name": NAME, "code": CODE})


def downgrade() -> None:
    # Удаляем только если по типу нет заявок — иначе FK orders.spec_order_id.
    op.get_bind().execute(sa.text(
        """
        DELETE FROM spec_orders s
        WHERE s.code = :code
          AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.spec_order_id = s.id)
        """
    ), {"code": CODE})
