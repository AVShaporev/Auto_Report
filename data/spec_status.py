from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_status import Spec_Status
from schema.spec_status import SpecStatusCreate, SpecStatusUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_spec_status_by_id(
    session: AsyncSession,
    spec_status_id: int,
    *,
    load_issues: bool = False
) -> Optional[Spec_Status]:
    """Получить статус по ID"""
    query = select(Spec_Status).where(Spec_Status.id == spec_status_id)

    if load_issues:
        query = query.options(selectinload(Spec_Status.issues))

    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_spec_status_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Status]:
    """Получить статус по наименованию"""
    query = select(Spec_Status).where(Spec_Status.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_spec_status_by_code(
    session: AsyncSession,
    code: str
) -> Optional[Spec_Status]:
    """Получить статус по машинному коду"""
    query = select(Spec_Status).where(Spec_Status.code == code)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_spec_status_all(
    session: AsyncSession,
    *,
    load_issues: bool = False
) -> List[Spec_Status]:
    """Получить все статусы"""
    query = select(Spec_Status).order_by(Spec_Status.name)

    if load_issues:
        query = query.options(selectinload(Spec_Status.issues))

    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_spec_status_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_issues: bool = False
) -> Tuple[List[Spec_Status], int]:
    """Получить список статусов с пагинацией"""
    query = select(Spec_Status)
    count_query = select(func.count()).select_from(Spec_Status)

    if search:
        search_filter = or_(
            Spec_Status.name.ilike(f"%{search}%"),
            Spec_Status.code.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if sort_by and hasattr(Spec_Status, sort_by):
        column = getattr(Spec_Status, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Status.name)

    if load_issues:
        query = query.options(selectinload(Spec_Status.issues))

    query = query.offset(skip).limit(limit)

    result = await session.execute(query)
    items = result.scalars().all()

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    return items, total

# ========== ПОЛУЧЕНИЕ ДЛЯ ВЫПАДАЮЩИХ СПИСКОВ ==========

@timer
async def get_spec_status_options(
    session: AsyncSession
) -> List[Spec_Status]:
    """Получить минимальную информацию о статусах для выпадающих списков"""
    query = select(Spec_Status).order_by(Spec_Status.id)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_spec_status_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли статус с таким наименованием"""
    query = select(Spec_Status).where(Spec_Status.name == name)
    if exclude_id:
        query = query.where(Spec_Status.id != exclude_id)

    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_spec_status_code_exists(
    session: AsyncSession,
    code: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли статус с таким кодом"""
    query = select(Spec_Status).where(Spec_Status.code == code)
    if exclude_id:
        query = query.where(Spec_Status.id != exclude_id)

    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_issues_by_spec_status(
    session: AsyncSession,
    spec_status_id: int
) -> int:
    """Посчитать количество неисправностей с данным статусом"""
    from model.issue import Issue

    query = select(func.count()).select_from(Issue).where(
        Issue.status_id == spec_status_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

@timer
async def create_spec_status(
    session: AsyncSession,
    spec_status_create: SpecStatusCreate
) -> Spec_Status:
    """Создать новый статус"""
    spec_status = Spec_Status(**spec_status_create.model_dump())
    session.add(spec_status)
    await session.commit()
    await session.refresh(spec_status)
    return spec_status

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_spec_status(
    session: AsyncSession,
    spec_status_id: int,
    spec_status_update: SpecStatusUpdate
) -> Optional[Spec_Status]:
    """Обновить статус"""
    spec_status = await get_spec_status_by_id(session, spec_status_id, load_issues=False)
    if not spec_status:
        return None

    update_data = spec_status_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_status, field):
            setattr(spec_status, field, value)

    await session.commit()
    await session.refresh(spec_status)
    return spec_status

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_spec_status(
    session: AsyncSession,
    spec_status_id: int
) -> bool:
    """Удалить статус"""
    spec_status = await session.get(Spec_Status, spec_status_id)
    if not spec_status:
        return False

    await session.delete(spec_status)
    await session.commit()
    return True
