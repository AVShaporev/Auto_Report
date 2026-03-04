from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_locality import Spec_Locality
from schema.spec_locality import SpecLocalityCreate, SpecLocalityUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    spec_locality_id: int,
    *,
    load_localities: bool = False
) -> Optional[Spec_Locality]:
    """
    Получить тип населенного пункта по ID
    
    Args:
        session: Сессия БД
        spec_locality_id: ID типа населенного пункта
        load_localities: Если True, загрузить связанные населенные пункты
    """
    query = select(Spec_Locality).where(Spec_Locality.id == spec_locality_id)
    
    if load_localities:
        query = query.options(selectinload(Spec_Locality.localitys))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Locality]:
    """Получить тип населенного пункта по названию"""
    query = select(Spec_Locality).where(Spec_Locality.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    *,
    load_localities: bool = False
) -> List[Spec_Locality]:
    """Получить все типы населенных пунктов"""
    query = select(Spec_Locality).order_by(Spec_Locality.name)
    
    if load_localities:
        query = query.options(selectinload(Spec_Locality.localitys))
    
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
    load_localities: bool = False
) -> Tuple[List[Spec_Locality], int]:
    """
    Получить список типов населенных пунктов с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Locality)
    count_query = select(func.count()).select_from(Spec_Locality)
    
    # Поиск по названию
    if search:
        search_filter = Spec_Locality.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Locality, sort_by):
        column = getattr(Spec_Locality, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Locality.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_localities:
        query = query.options(selectinload(Spec_Locality.localitys))
    
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
) -> List[Spec_Locality]:
    """
    Получить минимальную информацию о типах населенных пунктов для выпадающих списков
    """
    query = select(Spec_Locality).order_by(Spec_Locality.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли тип населенного пункта с таким названием"""
    query = select(Spec_Locality).where(Spec_Locality.name == name)
    if exclude_id:
        query = query.where(Spec_Locality.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

async def count_localities(
    session: AsyncSession,
    spec_locality_id: int
) -> int:
    """
    Посчитать количество населенных пунктов данного типа
    
    Это эффективнее, чем загружать все объекты через relationship
    """
    from model.locality import Locality
    
    query = select(func.count()).select_from(Locality).where(
        Locality.spec_locality_id == spec_locality_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    spec_locality_create: SpecLocalityCreate
) -> Spec_Locality:
    """Создать новый тип населенного пункта"""
    spec_locality = Spec_Locality(**spec_locality_create.dict())
    session.add(spec_locality)
    await session.commit()
    await session.refresh(spec_locality)
    return spec_locality

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    spec_locality_id: int,
    spec_locality_update: SpecLocalityUpdate
) -> Optional[Spec_Locality]:
    """Обновить тип населенного пункта"""
    spec_locality = await get_by_id(session, spec_locality_id, load_localities=False)
    if not spec_locality:
        return None
    
    update_data = spec_locality_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_locality, field):
            setattr(spec_locality, field, value)
    
    await session.commit()
    await session.refresh(spec_locality)
    return spec_locality

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    spec_locality_id: int
) -> bool:
    """Удалить тип населенного пункта"""
    spec_locality = await session.get(Spec_Locality, spec_locality_id)
    if not spec_locality:
        return False
    
    await session.delete(spec_locality)
    await session.commit()
    return True