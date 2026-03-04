from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_street import Spec_Street
from schema.spec_street import SpecStreetCreate, SpecStreetUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    spec_street_id: int,
    *,
    load_streets: bool = False
) -> Optional[Spec_Street]:
    """
    Получить тип улицы по ID
    
    Args:
        session: Сессия БД
        spec_street_id: ID типа улицы
        load_streets: Если True, загрузить связанные улицы
    """
    query = select(Spec_Street).where(Spec_Street.id == spec_street_id)
    
    if load_streets:
        query = query.options(selectinload(Spec_Street.streets))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Street]:
    """Получить тип улицы по названию"""
    query = select(Spec_Street).where(Spec_Street.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    *,
    load_streets: bool = False
) -> List[Spec_Street]:
    """Получить все типы улиц"""
    query = select(Spec_Street).order_by(Spec_Street.name)
    
    if load_streets:
        query = query.options(selectinload(Spec_Street.streets))
    
    result = await session.execute(query)
    return result.scalars().all()

async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_streets: bool = False
) -> Tuple[List[Spec_Street], int]:
    """
    Получить список типов улиц с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Street)
    count_query = select(func.count()).select_from(Spec_Street)
    
    # Поиск по названию
    if search:
        search_filter = Spec_Street.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Street, sort_by):
        column = getattr(Spec_Street, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Street.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_streets:
        query = query.options(selectinload(Spec_Street.streets))
    
    # Пагинация
    query = query.offset(skip).limit(limit)
    
    # Выполнение
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    return items, total

# ========== ПОЛУЧЕНИЕ ДЛЯ ВЫПАДАЮЩИХ СПИСКОВ ==========

async def get_options(
    session: AsyncSession
) -> List[Spec_Street]:
    """
    Получить минимальную информацию о типах улиц для выпадающих списков
    """
    query = select(Spec_Street).order_by(Spec_Street.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли тип улицы с таким названием"""
    query = select(Spec_Street).where(Spec_Street.name == name)
    if exclude_id:
        query = query.where(Spec_Street.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

async def count_streets(
    session: AsyncSession,
    spec_street_id: int
) -> int:
    """
    Посчитать количество улиц данного типа
    
    Это эффективнее, чем загружать все объекты через relationship
    """
    from model.street import Street
    
    query = select(func.count()).select_from(Street).where(
        Street.spec_street_id == spec_street_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    spec_street_create: SpecStreetCreate
) -> Spec_Street:
    """Создать новый тип улицы"""
    spec_street = Spec_Street(**spec_street_create.dict())
    session.add(spec_street)
    await session.commit()
    await session.refresh(spec_street)
    return spec_street

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    spec_street_id: int,
    spec_street_update: SpecStreetUpdate
) -> Optional[Spec_Street]:
    """Обновить тип улицы"""
    spec_street = await get_by_id(session, spec_street_id, load_streets=False)
    if not spec_street:
        return None
    
    update_data = spec_street_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_street, field):
            setattr(spec_street, field, value)
    
    await session.commit()
    await session.refresh(spec_street)
    return spec_street

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    spec_street_id: int
) -> bool:
    """Удалить тип улицы"""
    spec_street = await session.get(Spec_Street, spec_street_id)
    if not spec_street:
        return False
    
    await session.delete(spec_street)
    await session.commit()
    return True