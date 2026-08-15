from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from model.spec_order_status import Spec_Order_Status
from schema.spec_order_status import SpecOrderStatusCreate, SpecOrderStatusUpdate
from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_spec_order_status_all(session: AsyncSession) -> List[Spec_Order_Status]:
    """Все статусы отсортированы по id (порядок сида = порядок отображения)."""
    query = select(Spec_Order_Status).order_by(Spec_Order_Status.id)
    result = await session.execute(query)
    return result.scalars().all()


@timer
async def get_spec_order_status_by_id(
    session: AsyncSession, spec_order_status_id: int
) -> Optional[Spec_Order_Status]:
    query = select(Spec_Order_Status).where(Spec_Order_Status.id == spec_order_status_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_order_status_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> Tuple[List[Spec_Order_Status], int]:
    query = select(Spec_Order_Status)
    count_query = select(func.count()).select_from(Spec_Order_Status)

    if search:
        search_filter = or_(
            Spec_Order_Status.name.ilike(f"%{search}%"),
            Spec_Order_Status.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if sort_by and hasattr(Spec_Order_Status, sort_by):
        column = getattr(Spec_Order_Status, sort_by)
        query = query.order_by(column.desc() if sort_order == "desc" else column.asc())
    else:
        query = query.order_by(Spec_Order_Status.id)

    query = query.offset(skip).limit(limit)

    items = (await session.execute(query)).scalars().all()
    total = (await session.execute(count_query)).scalar()
    return items, total


async def get_default_status_id(session: AsyncSession) -> int:
    """id статуса по умолчанию (is_default=true). Fallback на MIN(id)."""
    result = await session.execute(
        select(Spec_Order_Status.id).where(Spec_Order_Status.is_default.is_(True))
    )
    sid = result.scalar_one_or_none()
    if sid is not None:
        return sid
    row2 = await session.execute(
        select(Spec_Order_Status.id).order_by(Spec_Order_Status.id).limit(1)
    )
    return row2.scalar_one()


# ========== ПРОВЕРКИ ==========

@timer
async def check_name_exists(
    session: AsyncSession, name: str, exclude_id: Optional[int] = None
) -> bool:
    query = select(Spec_Order_Status).where(Spec_Order_Status.name == name)
    if exclude_id:
        query = query.where(Spec_Order_Status.id != exclude_id)
    return (await session.execute(query)).scalar_one_or_none() is not None


@timer
async def count_orders_by_status(session: AsyncSession, status_id: int) -> int:
    """Сколько Order-записей используют этот статус."""
    from model.order import Order
    q = select(func.count()).select_from(Order).where(Order.status_id == status_id)
    return (await session.execute(q)).scalar() or 0


# ========== is_default snap ==========

async def _unset_current_default(session: AsyncSession, exclude_id: Optional[int] = None) -> None:
    """Снять is_default=true с текущей дефолтной строки (кроме exclude_id).

    Partial unique index требует чтобы только одна строка была default.
    Вызывается перед SET is_default = true у новой/обновляемой строки.
    """
    query = select(Spec_Order_Status).where(Spec_Order_Status.is_default.is_(True))
    if exclude_id is not None:
        query = query.where(Spec_Order_Status.id != exclude_id)
    for row in (await session.execute(query)).scalars().all():
        row.is_default = False


# ========== CRUD ==========

@timer
async def create_spec_order_status(
    session: AsyncSession, payload: SpecOrderStatusCreate
) -> Spec_Order_Status:
    if payload.is_default:
        await _unset_current_default(session)
    row = Spec_Order_Status(**payload.model_dump())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@timer
async def update_spec_order_status(
    session: AsyncSession, spec_order_status_id: int, payload: SpecOrderStatusUpdate
) -> Optional[Spec_Order_Status]:
    row = await get_spec_order_status_by_id(session, spec_order_status_id)
    if not row:
        return None

    data = payload.model_dump(exclude_unset=True)
    # is_default snap — если ставим true, снимем с текущего.
    if data.get('is_default') is True and not row.is_default:
        await _unset_current_default(session, exclude_id=spec_order_status_id)

    for field, value in data.items():
        setattr(row, field, value)

    await session.commit()
    await session.refresh(row)
    return row


@timer
async def delete_spec_order_status(
    session: AsyncSession, spec_order_status_id: int
) -> bool:
    row = await session.get(Spec_Order_Status, spec_order_status_id)
    if not row:
        return False
    await session.delete(row)
    await session.commit()
    return True
