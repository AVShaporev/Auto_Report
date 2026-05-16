from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Tuple

from model.spec_system import Spec_System
from model.objects_equipment import Objects_Equipment
from schema.spec_system import SpecSystemCreate, SpecSystemUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_spec_system_by_id(session: AsyncSession, spec_system_id: int) -> Optional[Spec_System]:
    query = select(Spec_System).where(Spec_System.id == spec_system_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_system_by_name(session: AsyncSession, name: str) -> Optional[Spec_System]:
    query = select(Spec_System).where(Spec_System.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_system_all(session: AsyncSession) -> List[Spec_System]:
    query = select(Spec_System).order_by(Spec_System.name)
    result = await session.execute(query)
    return result.scalars().all()


@timer
async def get_spec_system_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    is_fire_protection: Optional[bool] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> Tuple[List[Spec_System], int]:
    query = select(Spec_System)
    count_query = select(func.count()).select_from(Spec_System)

    if search:
        f = Spec_System.name.ilike(f"%{search}%")
        query = query.where(f)
        count_query = count_query.where(f)

    if is_fire_protection is not None:
        query = query.where(Spec_System.is_fire_protection == is_fire_protection)
        count_query = count_query.where(Spec_System.is_fire_protection == is_fire_protection)

    if sort_by and hasattr(Spec_System, sort_by):
        column = getattr(Spec_System, sort_by)
        query = query.order_by(column.desc() if sort_order == "desc" else column.asc())
    else:
        query = query.order_by(Spec_System.name)

    query = query.offset(skip).limit(limit)

    items = (await session.execute(query)).scalars().all()
    total = (await session.execute(count_query)).scalar() or 0
    return items, total


@timer
async def get_spec_system_options(session: AsyncSession) -> List[Spec_System]:
    query = select(Spec_System).order_by(Spec_System.name)
    result = await session.execute(query)
    return result.scalars().all()


# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_spec_system_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None,
) -> bool:
    query = select(Spec_System).where(Spec_System.name == name)
    if exclude_id:
        query = query.where(Spec_System.id != exclude_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


@timer
async def count_objects_equipments_by_spec_system(session: AsyncSession, spec_system_id: int) -> int:
    query = select(func.count()).select_from(Objects_Equipment).where(
        Objects_Equipment.spec_system_id == spec_system_id,
    )
    result = await session.execute(query)
    return result.scalar() or 0


# ========== СОЗДАНИЕ / ОБНОВЛЕНИЕ / УДАЛЕНИЕ ==========

@timer
async def create_spec_system(session: AsyncSession, payload: SpecSystemCreate) -> Spec_System:
    spec_system = Spec_System(**payload.model_dump())
    session.add(spec_system)
    await session.commit()
    await session.refresh(spec_system)
    return spec_system


@timer
async def update_spec_system(
    session: AsyncSession,
    spec_system_id: int,
    payload: SpecSystemUpdate,
) -> Optional[Spec_System]:
    spec_system = await get_spec_system_by_id(session, spec_system_id)
    if not spec_system:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_system, field):
            setattr(spec_system, field, value)

    await session.commit()
    await session.refresh(spec_system)
    return spec_system


@timer
async def delete_spec_system(session: AsyncSession, spec_system_id: int) -> bool:
    spec_system = await session.get(Spec_System, spec_system_id)
    if not spec_system:
        return False
    await session.delete(spec_system)
    await session.commit()
    return True
