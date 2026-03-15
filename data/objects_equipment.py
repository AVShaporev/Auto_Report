from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.objects_equipment import Objects_Equipment
from model.object import Object
from model.equipment import Equipment
from schema.objects_equipment import ObjectsEquipmentCreate, ObjectsEquipmentUpdate

from utils.timer import timer



# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_by_id(
    session: AsyncSession,
    link_id: int,
    *,
    load_relations: bool = False
) -> Optional[Objects_Equipment]:
    """
    Получить запись связи по ID
    
    Args:
        session: Сессия БД
        link_id: ID записи в objects_equipments
        load_relations: Если True, загрузить связанные объект и оборудование
    """
    query = select(Objects_Equipment).where(Objects_Equipment.id == link_id)
    
    if load_relations:
        query = query.options(
            selectinload(Objects_Equipment.object),
            selectinload(Objects_Equipment.equipment)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_object_and_equipment(
    session: AsyncSession,
    object_id: int,
    equipment_id: int
) -> Optional[Objects_Equipment]:
    """
    Получить запись связи по объекту и оборудованию
    """
    query = select(Objects_Equipment).where(
        and_(
            Objects_Equipment.object_id == object_id,
            Objects_Equipment.equipment_id == equipment_id
        )
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_object(
    session: AsyncSession,
    object_id: int,
    *,
    load_relations: bool = False
) -> List[Objects_Equipment]:
    """
    Получить всё оборудование для конкретного объекта
    """
    query = select(Objects_Equipment).where(
        Objects_Equipment.object_id == object_id
    ).order_by(Objects_Equipment.id)
    
    if load_relations:
        query = query.options(
            selectinload(Objects_Equipment.object),
            selectinload(Objects_Equipment.equipment)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_by_equipment(
    session: AsyncSession,
    equipment_id: int,
    *,
    load_relations: bool = False
) -> List[Objects_Equipment]:
    """
    Получить все объекты, где используется конкретное оборудование
    """
    query = select(Objects_Equipment).where(
        Objects_Equipment.equipment_id == equipment_id
    ).order_by(Objects_Equipment.id)
    
    if load_relations:
        query = query.options(
            selectinload(Objects_Equipment.object),
            selectinload(Objects_Equipment.equipment)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Objects_Equipment]:
    """
    Получить все связи объектов с оборудованием
    """
    query = select(Objects_Equipment).order_by(Objects_Equipment.object_id, Objects_Equipment.equipment_id)
    
    if load_relations:
        query = query.options(
            selectinload(Objects_Equipment.object),
            selectinload(Objects_Equipment.equipment)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    object_id: Optional[int] = None,
    equipment_id: Optional[int] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    *,
    load_relations: bool = False
) -> Tuple[List[Objects_Equipment], int]:
    """
    Получить список связей с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Objects_Equipment)
    count_query = select(func.count()).select_from(Objects_Equipment)
    
    # Фильтры
    if object_id:
        query = query.where(Objects_Equipment.object_id == object_id)
        count_query = count_query.where(Objects_Equipment.object_id == object_id)
    
    if equipment_id:
        query = query.where(Objects_Equipment.equipment_id == equipment_id)
        count_query = count_query.where(Objects_Equipment.equipment_id == equipment_id)
    
    # Сортировка
    if sort_by and hasattr(Objects_Equipment, sort_by):
        column = getattr(Objects_Equipment, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Objects_Equipment.object_id, Objects_Equipment.equipment_id)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Objects_Equipment.object),
            selectinload(Objects_Equipment.equipment)
        )
    
    # Пагинация
    query = query.offset(skip).limit(limit)
    
    # Выполнение
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    return items, total

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ ==========

@timer
async def check_exists(
    session: AsyncSession,
    object_id: int,
    equipment_id: int
) -> bool:
    """Проверить, существует ли уже такая связь"""
    query = select(Objects_Equipment).where(
        and_(
            Objects_Equipment.object_id == object_id,
            Objects_Equipment.equipment_id == equipment_id
        )
    )
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_object_exists(
    session: AsyncSession,
    object_id: int
) -> bool:
    """Проверить, существует ли объект"""
    query = select(Object).where(Object.id == object_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_equipment_exists(
    session: AsyncSession,
    equipment_id: int
) -> bool:
    """Проверить, существует ли оборудование"""
    query = select(Equipment).where(Equipment.id == equipment_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ ==========

@timer
async def count_by_object(
    session: AsyncSession,
    object_id: int
) -> int:
    """Посчитать количество единиц оборудования на объекте"""
    result = await session.execute(
        select(func.sum(Objects_Equipment.count)).where(
            Objects_Equipment.object_id == object_id
        )
    )
    return result.scalar() or 0

@timer
async def count_by_equipment(
    session: AsyncSession,
    equipment_id: int
) -> int:
    """Посчитать общее количество данного оборудования на всех объектах"""
    result = await session.execute(
        select(func.sum(Objects_Equipment.count)).where(
            Objects_Equipment.equipment_id == equipment_id
        )
    )
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

@timer
async def create(
    session: AsyncSession,
    link_create: ObjectsEquipmentCreate
) -> Objects_Equipment:
    """Создать новую связь объекта с оборудованием"""
    link = Objects_Equipment(**link_create.dict())
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update(
    session: AsyncSession,
    link_id: int,
    link_update: ObjectsEquipmentUpdate
) -> Optional[Objects_Equipment]:
    """Обновить связь объекта с оборудованием"""
    link = await get_by_id(session, link_id, load_relations=False)
    if not link:
        return None
    
    update_data = link_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(link, field):
            setattr(link, field, value)
    
    await session.commit()
    await session.refresh(link)
    return link

@timer
async def update_count(
    session: AsyncSession,
    object_id: int,
    equipment_id: int,
    new_count: int
) -> Optional[Objects_Equipment]:
    """Обновить количество для конкретной связки объект-оборудование"""
    link = await get_by_object_and_equipment(session, object_id, equipment_id)
    if not link:
        return None
    
    link.count = new_count
    await session.commit()
    await session.refresh(link)
    return link

# ========== УДАЛЕНИЕ ==========

@timer
async def delete(
    session: AsyncSession,
    link_id: int
) -> bool:
    """Удалить связь объекта с оборудованием"""
    link = await session.get(Objects_Equipment, link_id)
    if not link:
        return False
    
    await session.delete(link)
    await session.commit()
    return True

@timer
async def delete_by_object_and_equipment(
    session: AsyncSession,
    object_id: int,
    equipment_id: int
) -> bool:
    """Удалить связь объекта с оборудованием по объекту и оборудованию"""
    link = await get_by_object_and_equipment(session, object_id, equipment_id)
    if not link:
        return False
    
    await session.delete(link)
    await session.commit()
    return True