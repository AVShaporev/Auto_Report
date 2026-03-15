from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.period import Period
from schema.period import PeriodCreate, PeriodUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_by_id(
    session: AsyncSession,
    period_id: int,
    *,
    load_relations: bool = False
) -> Optional[Period]:
    """
    Получить период по ID
    
    Args:
        session: Сессия БД
        period_id: ID периода
        load_relations: Если True, загрузить связанные данные (objects, reports)
    """
    query = select(Period).where(Period.id == period_id)
    
    if load_relations:
        query = query.options(
            selectinload(Period.objects),
            selectinload(Period.reports)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Period]:
    """Получить период по названию"""
    query = select(Period).where(Period.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_period(
    session: AsyncSession,
    period: str
) -> Optional[Period]:
    """Получить период по периодичности"""
    query = select(Period).where(Period.period == period)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Period]:
    """Получить все периоды"""
    query = select(Period).order_by(Period.name)
    
    if load_relations:
        query = query.options(
            selectinload(Period.objects),
            selectinload(Period.reports)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_relations: bool = False
) -> Tuple[List[Period], int]:
    """
    Получить список периодов с пагинацией
    """
    # Базовый запрос
    query = select(Period)
    count_query = select(func.count()).select_from(Period)
    
    # Поиск по названию и периодичности
    if search:
        search_filter = or_(
            Period.name.ilike(f"%{search}%"),
            Period.period.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Period, sort_by):
        column = getattr(Period, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Period.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Period.objects),
            selectinload(Period.reports)
        )
    
    # Пагинация
    query = query.offset(skip).limit(limit)
    
    # Выполнение
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    return items, total

# ========== ПОЛУЧЕНИЕ ДЛЯ ВЫПАДАЮЩИХ СПИСКОВ ==========

@timer
async def get_options(
    session: AsyncSession
) -> List[Period]:
    """
    Получить минимальную информацию о периодах для выпадающих списков
    """
    query = select(Period).order_by(Period.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли период с таким названием"""
    query = select(Period).where(Period.name == name)
    if exclude_id:
        query = query.where(Period.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_period_exists(
    session: AsyncSession,
    period: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли период с такой периодичностью"""
    query = select(Period).where(Period.period == period)
    if exclude_id:
        query = query.where(Period.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_objects(
    session: AsyncSession,
    period_id: int
) -> int:
    """
    Посчитать количество объектов с данным периодом
    """
    from model.object import Object
    
    query = select(func.count()).select_from(Object).where(
        Object.period_id == period_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

@timer
async def count_reports(
    session: AsyncSession,
    period_id: int
) -> int:
    """
    Посчитать количество отчетов с данным периодом
    """
    from model.report import Report
    
    query = select(func.count()).select_from(Report).where(
        Report.period_id == period_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

@timer
async def create(
    session: AsyncSession,
    period_create: PeriodCreate
) -> Period:
    """Создать новый период"""
    period = Period(**period_create.dict())
    session.add(period)
    await session.commit()
    await session.refresh(period)
    return period

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update(
    session: AsyncSession,
    period_id: int,
    period_update: PeriodUpdate
) -> Optional[Period]:
    """Обновить период"""
    period = await get_by_id(session, period_id, load_relations=False)
    if not period:
        return None
    
    update_data = period_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(period, field):
            setattr(period, field, value)
    
    await session.commit()
    await session.refresh(period)
    return period

# ========== УДАЛЕНИЕ ==========

@timer
async def delete(
    session: AsyncSession,
    period_id: int
) -> bool:
    """Удалить период"""
    period = await session.get(Period, period_id)
    if not period:
        return False
    
    await session.delete(period)
    await session.commit()
    return True