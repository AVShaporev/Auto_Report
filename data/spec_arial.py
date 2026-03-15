from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_arial import Spec_Arial
from schema.spec_arial import SpecArialCreate, SpecArialUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_by_id(
    session: AsyncSession,
    spec_arial_id: int,
    *,
    load_arials: bool = False
) -> Optional[Spec_Arial]:
    """
    Получить тип района по ID
    
    Args:
        session: Сессия БД
        spec_arial_id: ID типа района
        load_arials: Если True, загрузить связанные районы
    """
    query = select(Spec_Arial).where(Spec_Arial.id == spec_arial_id)
    
    if load_arials:
        query = query.options(selectinload(Spec_Arial.arials))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Arial]:
    """Получить тип района по названию"""
    query = select(Spec_Arial).where(Spec_Arial.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_all(
    session: AsyncSession,
    *,
    load_arials: bool = False
) -> List[Spec_Arial]:
    """Получить все типы районов"""
    query = select(Spec_Arial).order_by(Spec_Arial.name)
    
    if load_arials:
        query = query.options(selectinload(Spec_Arial.arials))
    
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
    load_arials: bool = False
) -> Tuple[List[Spec_Arial], int]:
    """
    Получить список типов районов с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Arial)
    count_query = select(func.count()).select_from(Spec_Arial)
    
    # Поиск по названию
    if search:
        search_filter = Spec_Arial.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Arial, sort_by):
        column = getattr(Spec_Arial, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Arial.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_arials:
        query = query.options(selectinload(Spec_Arial.arials))
    
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
) -> List[Spec_Arial]:
    """
    Получить минимальную информацию о типах районов для выпадающих списков
    """
    query = select(Spec_Arial).order_by(Spec_Arial.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли тип района с таким названием"""
    query = select(Spec_Arial).where(Spec_Arial.name == name)
    if exclude_id:
        query = query.where(Spec_Arial.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_arials(
    session: AsyncSession,
    spec_arial_id: int
) -> int:
    """
    Посчитать количество районов данного типа
    
    Это эффективнее, чем загружать все объекты через relationship
    """
    from model.arial import Arial
    
    query = select(func.count()).select_from(Arial).where(
        Arial.spec_arial_id == spec_arial_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

@timer
async def create(
    session: AsyncSession,
    spec_arial_create: SpecArialCreate
) -> Spec_Arial:
    """Создать новый тип района"""
    spec_arial = Spec_Arial(**spec_arial_create.dict())
    session.add(spec_arial)
    await session.commit()
    await session.refresh(spec_arial)
    return spec_arial

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update(
    session: AsyncSession,
    spec_arial_id: int,
    spec_arial_update: SpecArialUpdate
) -> Optional[Spec_Arial]:
    """Обновить тип района"""
    spec_arial = await get_by_id(session, spec_arial_id, load_arials=False)
    if not spec_arial:
        return None
    
    update_data = spec_arial_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_arial, field):
            setattr(spec_arial, field, value)
    
    await session.commit()
    await session.refresh(spec_arial)
    return spec_arial

# ========== УДАЛЕНИЕ ==========

@timer
async def delete(
    session: AsyncSession,
    spec_arial_id: int
) -> bool:
    """Удалить тип района"""
    spec_arial = await session.get(Spec_Arial, spec_arial_id)
    if not spec_arial:
        return False
    
    await session.delete(spec_arial)
    await session.commit()
    return True