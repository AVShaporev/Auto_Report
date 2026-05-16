from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple, Dict

from model.region import Region
from model.organization import Organization
from model.object import Object
from schema.region import RegionCreate, RegionUpdate

from utils.timer import timer

@timer
async def get_organizations_count_by_region(session: AsyncSession) -> Dict[int, int]:
    """Возвращает словарь {region_id: количество организаций}."""
    query = select(Region.id, func.count(Organization.id)).join(
                                                                    Organization, Organization.region_id == Region.id, isouter=True
                                                                ).group_by(Region.id)
    result = await session.execute(query)
    return dict(result.all())

@timer
async def get_objects_count_by_region(session: AsyncSession) -> Dict[int, int]:
    """Возвращает словарь {region_id: количество объектов}."""
    query = select(Region.id, func.count(Object.id)).join(
                                                            Object, Object.region_id == Region.id, isouter=True
                                                        ).group_by(Region.id)
    result = await session.execute(query)
    return dict(result.all())


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_region_by_id(
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

@timer
async def get_region_by_name(
                            session: AsyncSession,
                            name: str
                            ) -> Optional[Region]:
    """Получить регион по названию"""
    query = select(Region).where(Region.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_region_by_symbol(
                                session: AsyncSession,
                                symbol: str
                                ) -> Optional[Region]:
    """Получить регион по символьному коду"""
    query = select(Region).where(Region.symbol == symbol)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_region_all(
                        session: AsyncSession,
                        *,
                        load_relations: bool = False
                        ) -> List[Region]:
    """Получить все регионы"""
    query = select(Region).order_by(Region.name)
    
    if load_relations:
        # загружаем только spec_region (отношение многие-к-одному)
        query = query.options(selectinload(Region.spec_region))
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_region_paginated(
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

@timer
async def get_region_options(
                            session: AsyncSession
                            ) -> List[Region]:
    """
    Получить минимальную информацию о регионах для выпадающих списков
    """
    query = select(Region).order_by(Region.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_region_name_exists(
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

@timer
async def check_region_symbol_exists(
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

@timer
async def check_region_spec_region_exists(
                                            session: AsyncSession,
                                            spec_region_id: int
                                            ) -> bool:
    """Проверить, существует ли тип региона с указанным ID"""
    from model.spec_region import Spec_Region
    
    query = select(Spec_Region).where(Spec_Region.id == spec_region_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_region_organizations(
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

@timer
async def count_region_objects(
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

@timer
async def create_region(
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

@timer
async def update_region(
                        session: AsyncSession,
                        region_id: int,
                        region_update: RegionUpdate
                        ) -> Optional[Region]:
    """Обновить регион"""
    region = await get_region_by_id(session, region_id, load_relations=False)
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

@timer
async def delete_region(
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