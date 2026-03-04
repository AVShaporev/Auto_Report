from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_room import Spec_Room
from schema.spec_room import SpecRoomCreate, SpecRoomUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    spec_room_id: int,
    *,
    load_relations: bool = False
) -> Optional[Spec_Room]:
    """
    Получить тип помещения по ID
    
    Args:
        session: Сессия БД
        spec_room_id: ID типа помещения
        load_relations: Если True, загрузить связанные данные (organizations, objects)
    """
    query = select(Spec_Room).where(Spec_Room.id == spec_room_id)
    
    if load_relations:
        query = query.options(
            selectinload(Spec_Room.organizations),
            selectinload(Spec_Room.objects)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Room]:
    """Получить тип помещения по названию"""
    query = select(Spec_Room).where(Spec_Room.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Spec_Room]:
    """Получить все типы помещений"""
    query = select(Spec_Room).order_by(Spec_Room.name)
    
    if load_relations:
        query = query.options(
            selectinload(Spec_Room.organizations),
            selectinload(Spec_Room.objects)
        )
    
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
    load_relations: bool = False
) -> Tuple[List[Spec_Room], int]:
    """
    Получить список типов помещений с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Room)
    count_query = select(func.count()).select_from(Spec_Room)
    
    # Поиск по названию
    if search:
        search_filter = Spec_Room.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Room, sort_by):
        column = getattr(Spec_Room, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Room.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Spec_Room.organizations),
            selectinload(Spec_Room.objects)
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
) -> List[Spec_Room]:
    """
    Получить минимальную информацию о типах помещений для выпадающих списков
    """
    query = select(Spec_Room).order_by(Spec_Room.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли тип помещения с таким названием"""
    query = select(Spec_Room).where(Spec_Room.name == name)
    if exclude_id:
        query = query.where(Spec_Room.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

async def count_organizations(
    session: AsyncSession,
    spec_room_id: int
) -> int:
    """
    Посчитать количество организаций с данным типом помещения
    """
    from model.organization import Organization
    
    query = select(func.count()).select_from(Organization).where(
        Organization.spec_room_id == spec_room_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

async def count_objects(
    session: AsyncSession,
    spec_room_id: int
) -> int:
    """
    Посчитать количество объектов с данным типом помещения
    """
    from model.object import Object
    
    query = select(func.count()).select_from(Object).where(
        Object.spec_room_id == spec_room_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    spec_room_create: SpecRoomCreate
) -> Spec_Room:
    """Создать новый тип помещения"""
    spec_room = Spec_Room(**spec_room_create.dict())
    session.add(spec_room)
    await session.commit()
    await session.refresh(spec_room)
    return spec_room

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    spec_room_id: int,
    spec_room_update: SpecRoomUpdate
) -> Optional[Spec_Room]:
    """Обновить тип помещения"""
    spec_room = await get_by_id(session, spec_room_id, load_relations=False)
    if not spec_room:
        return None
    
    update_data = spec_room_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_room, field):
            setattr(spec_room, field, value)
    
    await session.commit()
    await session.refresh(spec_room)
    return spec_room

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    spec_room_id: int
) -> bool:
    """Удалить тип помещения"""
    spec_room = await session.get(Spec_Room, spec_room_id)
    if not spec_room:
        return False
    
    await session.delete(spec_room)
    await session.commit()
    return True