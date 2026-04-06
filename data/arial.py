from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple, Dict

from model.arial import Arial
from model.organization import Organization
from model.object import Object
from schema.arial import ArialCreate, ArialUpdate

from utils.timer import timer

@timer
async def get_organizations_count_by_arial(session: AsyncSession) -> Dict[int, int]:
    """Возвращает словарь {arial_id: количество организаций}."""
    query = select(Arial.id, func.count(Organization.id)).join(
        Organization, Organization.arial_id == Arial.id, isouter=True
    ).group_by(Arial.id)
    result = await session.execute(query)
    return dict(result.all())

@timer
async def get_objects_count_by_arial(session: AsyncSession) -> Dict[int, int]:
    """Возвращает словарь {arial_id: количество объектов}."""
    query = select(Arial.id, func.count(Object.id)).join(
        Object, Object.arial_id == Arial.id, isouter=True
    ).group_by(Arial.id)
    result = await session.execute(query)
    return dict(result.all())

# ========== ПОЛУЧЕНИЕ ==========
@timer
async def get_arial_by_id(
    session: AsyncSession,
    arial_id: int,
    *,
    load_relations: bool = False
) -> Optional[Arial]:
    """
    Получить район по ID
    
    Args:
        session: Сессия БД
        arial_id: ID района
        load_relations: Если True, загрузить связанные данные (spec_arial, organizations, objects)
    """
    query = select(Arial).where(Arial.id == arial_id)
    
    if load_relations:
        query = query.options(
            selectinload(Arial.spec_arial),
            selectinload(Arial.organizations),
            selectinload(Arial.objects)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_arial_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Arial]:
    """Получить район по названию"""
    query = select(Arial).where(Arial.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_arial_all(
                        session: AsyncSession,
                        *,
                        load_relations: bool = False
                        ) -> List[Arial]:
    """Получить все районы"""
    query = select(Arial).order_by(Arial.name)
    
    if load_relations:
        query = query.options(
            selectinload(Arial.spec_arial),
            selectinload(Arial.organizations),
            selectinload(Arial.objects)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_arial_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    spec_arial_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_relations: bool = False
) -> Tuple[List[Arial], int]:
    """
    Получить список районов с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Arial)
    count_query = select(func.count()).select_from(Arial)
    
    # Поиск по названию
    if search:
        search_filter = Arial.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтр по типу района
    if spec_arial_id:
        query = query.where(Arial.spec_arial_id == spec_arial_id)
        count_query = count_query.where(Arial.spec_arial_id == spec_arial_id)
    
    # Сортировка
    if sort_by and hasattr(Arial, sort_by):
        column = getattr(Arial, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Arial.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Arial.spec_arial),
            selectinload(Arial.organizations),
            selectinload(Arial.objects)
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
async def get_arial_options(
    session: AsyncSession
) -> List[Arial]:
    """
    Получить минимальную информацию о районах для выпадающих списков
    """
    query = select(Arial).order_by(Arial.name)
    result = await session.execute(query)
    return result.scalars().all()

async def get_arial_options_by_spec_arial(
    session: AsyncSession,
    spec_arial_id: int
) -> List[Arial]:
    """
    Получить минимальную информацию о районах для выпадающих списков по типу района
    """
    query = select(Arial).where(Arial.spec_arial_id == spec_arial_id).order_by(Arial.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========
@timer
async def check_arial_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли район с таким названием"""
    query = select(Arial).where(Arial.name == name)
    if exclude_id:
        query = query.where(Arial.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ ТИПА РАЙОНА ==========
@timer
async def check_arial_spec_arial_exists(
    session: AsyncSession,
    spec_arial_id: int
) -> bool:
    """Проверить, существует ли тип района с указанным ID"""
    from model.spec_arial import Spec_Arial
    
    query = select(Spec_Arial).where(Spec_Arial.id == spec_arial_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========
@timer
async def count_arial_organizations(
    session: AsyncSession,
    arial_id: int
) -> int:
    """
    Посчитать количество организаций в районе
    """
    from model.organization import Organization
    
    query = select(func.count()).select_from(Organization).where(
        Organization.arial_id == arial_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

@timer
async def count_arial_objects(
    session: AsyncSession,
    arial_id: int
) -> int:
    """
    Посчитать количество объектов в районе
    """
    from model.object import Object
    
    query = select(func.count()).select_from(Object).where(
        Object.arial_id == arial_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========
@timer
async def create_arial(
    session: AsyncSession,
    arial_create: ArialCreate
) -> Arial:
    """Создать новый район"""
    arial = Arial(**arial_create.dict())
    session.add(arial)
    await session.commit()
    await session.refresh(arial)
    return arial

# ========== ОБНОВЛЕНИЕ ==========
@timer
async def update_arial(
    session: AsyncSession,
    arial_id: int,
    arial_update: ArialUpdate
) -> Optional[Arial]:
    """Обновить район"""
    arial = await get_by_id(session, arial_id, load_relations=False)
    if not arial:
        return None
    
    update_data = arial_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(arial, field):
            setattr(arial, field, value)
    
    await session.commit()
    await session.refresh(arial)
    return arial

# ========== УДАЛЕНИЕ ==========
@timer
async def delete_arial(
    session: AsyncSession,
    arial_id: int
) -> bool:
    """Удалить район"""
    arial = await session.get(Arial, arial_id)
    if not arial:
        return False
    
    await session.delete(arial)
    await session.commit()
    return True