from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.street import Street
from schema.street import StreetCreate, StreetUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    street_id: int,
    *,
    load_relations: bool = False
) -> Optional[Street]:
    """
    Получить улицу по ID
    
    Args:
        session: Сессия БД
        street_id: ID улицы
        load_relations: Если True, загрузить связанные данные (spec_street, organizations, objects)
    """
    query = select(Street).where(Street.id == street_id)
    
    if load_relations:
        query = query.options(
            selectinload(Street.spec_street),
            selectinload(Street.organizations),
            selectinload(Street.objects)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Street]:
    """Получить улицу по названию"""
    query = select(Street).where(Street.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Street]:
    """Получить все улицы"""
    query = select(Street).order_by(Street.name)
    
    if load_relations:
        query = query.options(
            selectinload(Street.spec_street),
            selectinload(Street.organizations),
            selectinload(Street.objects)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    spec_street_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_relations: bool = False
) -> Tuple[List[Street], int]:
    """
    Получить список улиц с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Street)
    count_query = select(func.count()).select_from(Street)
    
    # Поиск по названию
    if search:
        search_filter = Street.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтр по типу улицы
    if spec_street_id:
        query = query.where(Street.spec_street_id == spec_street_id)
        count_query = count_query.where(Street.spec_street_id == spec_street_id)
    
    # Сортировка
    if sort_by and hasattr(Street, sort_by):
        column = getattr(Street, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Street.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Street.spec_street),
            selectinload(Street.organizations),
            selectinload(Street.objects)
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
) -> List[Street]:
    """
    Получить минимальную информацию об улицах для выпадающих списков
    """
    query = select(Street).order_by(Street.name)
    result = await session.execute(query)
    return result.scalars().all()

async def get_options_by_spec_street(
    session: AsyncSession,
    spec_street_id: int
) -> List[Street]:
    """
    Получить минимальную информацию об улицах для выпадающих списков по типу
    """
    query = select(Street).where(Street.spec_street_id == spec_street_id).order_by(Street.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли улица с таким названием"""
    query = select(Street).where(Street.name == name)
    if exclude_id:
        query = query.where(Street.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ ТИПА УЛИЦЫ ==========

async def check_spec_street_exists(
    session: AsyncSession,
    spec_street_id: int
) -> bool:
    """Проверить, существует ли тип улицы с указанным ID"""
    from model.spec_street import Spec_Street
    
    query = select(Spec_Street).where(Spec_Street.id == spec_street_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

async def count_organizations(
    session: AsyncSession,
    street_id: int
) -> int:
    """
    Посчитать количество организаций на улице
    """
    from model.organization import Organization
    
    query = select(func.count()).select_from(Organization).where(
        Organization.street_id == street_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

async def count_objects(
    session: AsyncSession,
    street_id: int
) -> int:
    """
    Посчитать количество объектов на улице
    """
    from model.object import Object
    
    query = select(func.count()).select_from(Object).where(
        Object.street_id == street_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    street_create: StreetCreate
) -> Street:
    """Создать новую улицу"""
    street = Street(**street_create.dict())
    session.add(street)
    await session.commit()
    await session.refresh(street)
    return street

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    street_id: int,
    street_update: StreetUpdate
) -> Optional[Street]:
    """Обновить улицу"""
    street = await get_by_id(session, street_id, load_relations=False)
    if not street:
        return None
    
    update_data = street_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(street, field):
            setattr(street, field, value)
    
    await session.commit()
    await session.refresh(street)
    return street

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    street_id: int
) -> bool:
    """Удалить улицу"""
    street = await session.get(Street, street_id)
    if not street:
        return False
    
    await session.delete(street)
    await session.commit()
    return True