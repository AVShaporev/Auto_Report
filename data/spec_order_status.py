from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from model.spec_order_status import Spec_Order_Status
from utils.timer import timer


# Read-only справочник. Сидится миграцией e8f9a0b1c2d3 (4 системные строки).
# CRUD не нужен — статусы фиксированы. Если админ через прямой SQL захочет
# добавить/переименовать — фронт подхватит через /options.


@timer
async def get_spec_order_status_all(session: AsyncSession) -> List[Spec_Order_Status]:
    """Все статусы отсортированы по id (порядок сида = порядок отображения)."""
    query = select(Spec_Order_Status).order_by(Spec_Order_Status.id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_default_status_id(session: AsyncSession) -> int:
    """id статуса по умолчанию (is_default=true).

    Используется autogen'ом и create_order когда клиент не передал status_id.
    Partial unique index гарантирует одну такую строку. Если её вдруг нет
    (сид не прогнан?) — вернём MIN(id) как fallback.
    """
    result = await session.execute(
        select(Spec_Order_Status.id).where(Spec_Order_Status.is_default.is_(True))
    )
    sid = result.scalar_one_or_none()
    if sid is not None:
        return sid
    # Fallback: первый по id (обычно "Новая" после сида).
    result2 = await session.execute(
        select(Spec_Order_Status.id).order_by(Spec_Order_Status.id).limit(1)
    )
    return result2.scalar_one()
