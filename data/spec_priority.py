from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_priority import Spec_Priority
from schema.spec_priority import SpecPriorityCreate, SpecPriorityUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_spec_priority_by_id(
    session: AsyncSession,
    spec_priority_id: int,
    *,
    load_issues: bool = False
) -> Optional[Spec_Priority]:
    """Получить приоритет по ID"""
    query = select(Spec_Priority).where(Spec_Priority.id == spec_priority_id)

    if load_issues:
        query = query.options(selectinload(Spec_Priority.issues))

    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_priority_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Priority]:
    """Получить приоритет по наименованию"""
    query = select(Spec_Priority).where(Spec_Priority.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_priority_by_code(
    session: AsyncSession,
    code: str
) -> Optional[Spec_Priority]:
    """Получить приоритет по машинному коду"""
    query = select(Spec_Priority).where(Spec_Priority.code == code)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_priority_all(
    session: AsyncSession,
    *,
    load_issues: bool = False
) -> List[Spec_Priority]:
    """Получить все приоритеты"""
    query = select(Spec_Priority).order_by(Spec_Priority.id)

    if load_issues:
        query = query.options(selectinload(Spec_Priority.issues))

    result = await session.execute(query)
    return result.scalars().all()


@timer
async def get_spec_priority_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    *,
    load_issues: bool = False
) -> Tuple[List[Spec_Priority], int]:
    """Получить список приоритетов с пагинацией"""
    query = select(Spec_Priority)
    count_query = select(func.count()).select_from(Spec_Priority)

    if search:
        search_filter = or_(
            Spec_Priority.name.ilike(f"%{search}%"),
            Spec_Priority.code.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if sort_by and hasattr(Spec_Priority, sort_by):
        column = getattr(Spec_Priority, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Priority.id)

    if load_issues:
        query = query.options(selectinload(Spec_Priority.issues))

    query = query.offset(skip).limit(limit)

    result = await session.execute(query)
    items = result.scalars().all()

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    return items, total


@timer
async def get_spec_priority_options(
    session: AsyncSession
) -> List[Spec_Priority]:
    """Минимальная инфа о приоритетах для выпадающих списков"""
    query = select(Spec_Priority).order_by(Spec_Priority.id)
    result = await session.execute(query)
    return result.scalars().all()


# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_spec_priority_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    query = select(Spec_Priority).where(Spec_Priority.name == name)
    if exclude_id:
        query = query.where(Spec_Priority.id != exclude_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


@timer
async def check_spec_priority_code_exists(
    session: AsyncSession,
    code: str,
    exclude_id: Optional[int] = None
) -> bool:
    query = select(Spec_Priority).where(Spec_Priority.code == code)
    if exclude_id:
        query = query.where(Spec_Priority.id != exclude_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


# ========== ПОДСЧЕТ СВЯЗАННЫХ ==========

@timer
async def count_issues_by_spec_priority(
    session: AsyncSession,
    spec_priority_id: int
) -> int:
    from model.issue import Issue
    query = select(func.count()).select_from(Issue).where(
        Issue.priority_id == spec_priority_id
    )
    result = await session.execute(query)
    return result.scalar() or 0


# ========== СОЗДАНИЕ ==========

@timer
async def create_spec_priority(
    session: AsyncSession,
    spec_priority_create: SpecPriorityCreate
) -> Spec_Priority:
    spec_priority = Spec_Priority(**spec_priority_create.model_dump())
    session.add(spec_priority)
    await session.commit()
    await session.refresh(spec_priority)
    return spec_priority


# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_spec_priority(
    session: AsyncSession,
    spec_priority_id: int,
    spec_priority_update: SpecPriorityUpdate
) -> Optional[Spec_Priority]:
    spec_priority = await get_spec_priority_by_id(session, spec_priority_id, load_issues=False)
    if not spec_priority:
        return None

    update_data = spec_priority_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_priority, field):
            setattr(spec_priority, field, value)

    await session.commit()
    await session.refresh(spec_priority)
    return spec_priority


# ========== УДАЛЕНИЕ ==========

@timer
async def delete_spec_priority(
    session: AsyncSession,
    spec_priority_id: int
) -> bool:
    spec_priority = await session.get(Spec_Priority, spec_priority_id)
    if not spec_priority:
        return False
    await session.delete(spec_priority)
    await session.commit()
    return True
