from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_region import Spec_Region
from schema.spec_region import SpecRegionCreate, SpecRegionUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_spec_region_by_id(
                                session: AsyncSession,
                                spec_region_id: int,
                                *,
                                load_regions: bool = False
                                ) -> Optional[Spec_Region]:
    """
    Получить тип региона по ID
    
    Args:
        session: Сессия БД
        spec_region_id: ID типа региона
        load_regions: Если True, загрузить связанные регионы
    """
    query = select(Spec_Region).where(Spec_Region.id == spec_region_id)
    
    if load_regions:
        query = query.options(selectinload(Spec_Region.regions))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_spec_region_by_name(
                                    session: AsyncSession,
                                    name: str
                                    ) -> Optional[Spec_Region]:
    """Получить тип региона по названию"""
    query = select(Spec_Region).where(Spec_Region.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_spec_region_all(
                                session: AsyncSession,
                                *,
                                load_regions: bool = False
                                ) -> List[Spec_Region]:
    """Получить все типы регионов"""
    query = select(Spec_Region).order_by(Spec_Region.name)
    
    if load_regions:
        query = query.options(selectinload(Spec_Region.regions))
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_spec_region_paginated(
                                    session: AsyncSession,
                                    skip: int = 0,
                                    limit: int = 20,
                                    search: Optional[str] = None,
                                    sort_by: str = "name",
                                    sort_order: str = "asc",
                                    *,
                                    load_regions: bool = False
                                    ) -> Tuple[List[Spec_Region], int]:
    """
    Получить список типов регионов с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Region)
    count_query = select(func.count()).select_from(Spec_Region)
    
    # Поиск по названию
    if search:
        search_filter = Spec_Region.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Region, sort_by):
        column = getattr(Spec_Region, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Region.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_regions:
        query = query.options(selectinload(Spec_Region.regions))
    
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
async def get_spec_region_options(
                                    session: AsyncSession
                                    ) -> List[Spec_Region]:
    """
    Получить минимальную информацию о типах регионов для выпадающих списков
    """
    query = select(Spec_Region).order_by(Spec_Region.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_spec_region_name_exists(
                                        session: AsyncSession,
                                        name: str,
                                        exclude_id: Optional[int] = None
                                        ) -> bool:
    """Проверить, существует ли тип региона с таким названием"""
    query = select(Spec_Region).where(Spec_Region.name == name)
    if exclude_id:
        query = query.where(Spec_Region.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_spec_region_regions(
                        session: AsyncSession,
                        spec_region_id: int
                        ) -> int:
    """
    Посчитать количество регионов данного типа
    
    Это эффективнее, чем загружать все объекты через relationship
    """
    from model.region import Region
    
    query = select(func.count()).select_from(Region).where(
        Region.spec_region_id == spec_region_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

@timer
async def create_spec_region(
                            session: AsyncSession,
                            spec_region_create: SpecRegionCreate
                            ) -> Spec_Region:
    """Создать новый тип региона"""
    spec_region = Spec_Region(**spec_region_create.dict())
    session.add(spec_region)
    await session.commit()
    await session.refresh(spec_region)
    return spec_region

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_spec_region(
                            session: AsyncSession,
                            spec_region_id: int,
                            spec_region_update: SpecRegionUpdate
                            ) -> Optional[Spec_Region]:
    """Обновить тип региона"""
    spec_region = await get_spec_region_by_id(session, spec_region_id, load_regions=False)
    if not spec_region:
        return None
    
    update_data = spec_region_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_region, field):
            setattr(spec_region, field, value)
    
    await session.commit()
    await session.refresh(spec_region)
    return spec_region

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_spec_region(
                                session: AsyncSession,
                                spec_region_id: int
                            ) -> bool:
    """Удалить тип региона"""
    spec_region = await session.get(Spec_Region, spec_region_id)
    if not spec_region:
        return False
    
    await session.delete(spec_region)
    await session.commit()
    return True