from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from model.spec_order_status import Spec_Order_Status
from utils.timer import timer


# Read-only справочник. Сидится миграцией e8f9a0b1c2d3 (4 системные строки).
# CRUD не нужен — статусы фиксированы кодом (см. Literal-валидатор в
# api/order.py:update_order_status).


@timer
async def get_spec_order_status_all(session: AsyncSession) -> List[Spec_Order_Status]:
    """Все статусы в порядке display_order (для селектов на фронте)."""
    query = select(Spec_Order_Status).order_by(
        Spec_Order_Status.display_order, Spec_Order_Status.id
    )
    result = await session.execute(query)
    return result.scalars().all()


@timer
async def get_spec_order_status_by_code(
    session: AsyncSession, code: str
) -> Optional[Spec_Order_Status]:
    query = select(Spec_Order_Status).where(Spec_Order_Status.code == code)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_status_id_by_code(
    session: AsyncSession, code: str
) -> Optional[int]:
    """Resolve строковый код → id. Возвращает None если код не найден
    (защиты нет: service должен обработать, обычно 400 Bad Request или
    fallback на код 'new'). Один SELECT id без загрузки объекта."""
    query = select(Spec_Order_Status.id).where(Spec_Order_Status.code == code)
    result = await session.execute(query)
    return result.scalar_one_or_none()
