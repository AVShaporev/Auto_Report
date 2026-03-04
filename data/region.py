from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.region import Region
from schema.region import RegionCreate, RegionUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    region_id: int,
    *,
    load_relations: bool = False
) -> Optional[Region]:
    """
    Получить регион по ID
    
    Args:
        session: Сессия БД
        region_id: ID региона
        load_relations: Если True, загрузить связанные данные (spec_region, organizations, objects)
    """
    query = select(Region).where(Region.id == region_id)
    
    if load_relations:
        query = query.options(
            selectinload(Region.spec_region),
            selectinload(Region.organizations),
            selectinload(Region.objects)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Region]:
    """Получить регион по названию"""
    query = select(Region).where(Region.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_symbol(
    session: AsyncSession,
    symbol: str
) -> Optional[Region]:
    """Получить регион по символьному коду"""
    query = select(Region).where(Region.symbol == symbol)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Region]:
    """Получить все регионы"""
    query = select(Region).order_by(Region.name)
    
    if load_relations:
        query = query.options(
            selectinload(Region.spec_region),
            selectinload(Region.organizations),
            selectinload(Region.objects)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    spec_region_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_relations: bool = False
) -> Tuple[List[Region], int]:
    """
    Получить список регионов с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Region)
    count_query = select(func.count()).select_from(Region)
    
    # Поиск по названию или символу
    if search:
        search_filter = or_(
            Region.name.ilike(f"%{search}%"),
            Region.symbol.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтр по типу региона
    if spec_region_id:
        query = query.where(Region.spec_region_id == spec_region_id)
        count_query = count_query.where(Region.spec_region_id == spec_region_id)
    
    # Сортировка
    if sort_by and hasattr(Region, sort_by):
        column = getattr(Region, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Region.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Region.spec_region),
            selectinload(Region.organizations),
            selectinload(Region.objects)
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

async def get_options(
    session: AsyncSession
) -> List[Region]:
    """
    Получить минимальную информацию о регионах для выпадающих списков
    """
    query = select(Region).order_by(Region.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли регион с таким названием"""
    query = select(Region).where(Region.name == name)
    if exclude_id:
        query = query.where(Region.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_symbol_exists(
    session: AsyncSession,
    symbol: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли регион с таким символьным кодом"""
    query = select(Region).where(Region.symbol == symbol)
    if exclude_id:
        query = query.where(Region.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ ТИПА РЕГИОНА ==========

async def check_spec_region_exists(
    session: AsyncSession,
    spec_region_id: int
) -> bool:
    """Проверить, существует ли тип региона с указанным ID"""
    from model.spec_region import Spec_Region
    
    query = select(Spec_Region).where(Spec_Region.id == spec_region_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

async def count_organizations(
    session: AsyncSession,
    region_id: int
) -> int:
    """
    Посчитать количество организаций в регионе
    """
    from model.organization import Organization
    
    query = select(func.count()).select_from(Organization).where(
        Organization.region_id == region_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

async def count_objects(
    session: AsyncSession,
    region_id: int
) -> int:
    """
    Посчитать количество объектов в регионе
    """
    from model.object import Object
    
    query = select(func.count()).select_from(Object).where(
        Object.region_id == region_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    region_create: RegionCreate
) -> Region:
    """Создать новый регион"""
    region = Region(**region_create.dict())
    session.add(region)
    await session.commit()
    await session.refresh(region)
    return region

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    region_id: int,
    region_update: RegionUpdate
) -> Optional[Region]:
    """Обновить регион"""
    region = await get_by_id(session, region_id, load_relations=False)
    if not region:
        return None
    
    update_data = region_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(region, field):
            setattr(region, field, value)
    
    await session.commit()
    await session.refresh(region)
    return region

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    region_id: int
) -> bool:
    """Удалить регион"""
    region = await session.get(Region, region_id)
    if not region:
        return False
    
    await session.delete(region)
    await session.commit()
    return True