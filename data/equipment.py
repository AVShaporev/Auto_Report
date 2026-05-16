from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.equipment import Equipment
from model.objects_equipment import Objects_Equipment
from schema.equipment import EquipmentCreate, EquipmentUpdate

from utils.timer import timer



# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_equipment_by_id(
    session: AsyncSession,
    equipment_id: int,
    *,
    load_relations: bool = False
) -> Optional[Equipment]:
    """Получить оборудование по ID"""
    query = select(Equipment).where(Equipment.id == equipment_id)

    if load_relations:
        query = query.options(selectinload(Equipment.spec_equipment))

    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_equipment_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Equipment]:
    """Получить оборудование по названию"""
    query = select(Equipment).where(Equipment.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_equipment_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Equipment]:
    """Получить все оборудование"""
    query = select(Equipment).order_by(Equipment.name)

    if load_relations:
        query = query.options(selectinload(Equipment.spec_equipment))

    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_equipment_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    spec_equipment_id: Optional[int] = None,
    object_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_relations: bool = False
) -> Tuple[List[Equipment], int]:
    """
    Получить список оборудования с пагинацией и фильтрацией
    """
    query = select(Equipment)
    count_query = select(func.count()).select_from(Equipment)

    # Если указан object_id, фильтруем по связи с объектом через JOIN
    if object_id:
        query = query.join(
            Objects_Equipment,
            Objects_Equipment.equipment_id == Equipment.id
        ).where(Objects_Equipment.object_id == object_id)

        count_query = count_query.join(
            Objects_Equipment,
            Objects_Equipment.equipment_id == Equipment.id
        ).where(Objects_Equipment.object_id == object_id)

    # Поиск по названию
    if search:
        search_filter = Equipment.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Фильтр по типу оборудования
    if spec_equipment_id:
        query = query.where(Equipment.spec_equipment_id == spec_equipment_id)
        count_query = count_query.where(Equipment.spec_equipment_id == spec_equipment_id)

    # Фильтр по активности
    if is_active is not None:
        query = query.where(Equipment.is_active == is_active)
        count_query = count_query.where(Equipment.is_active == is_active)

    # Сортировка
    if sort_by and hasattr(Equipment, sort_by):
        column = getattr(Equipment, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Equipment.name)

    if load_relations:
        query = query.options(selectinload(Equipment.spec_equipment))

    query = query.offset(skip).limit(limit)

    result = await session.execute(query)
    items = result.scalars().all()

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    return items, total

# ========== ПОЛУЧЕНИЕ ДЛЯ ВЫПАДАЮЩИХ СПИСКОВ ==========

@timer
async def get_equipment_options(
    session: AsyncSession,
    object_id: Optional[int] = None,
    is_active: Optional[bool] = None
) -> List[Equipment]:
    """Получить минимальную информацию об оборудовании для выпадающих списков"""
    query = select(Equipment).order_by(Equipment.name)

    if object_id:
        query = query.join(
            Objects_Equipment,
            Objects_Equipment.equipment_id == Equipment.id
        ).where(Objects_Equipment.object_id == object_id)

    if is_active is not None:
        query = query.where(Equipment.is_active == is_active)

    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_equipment_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли оборудование с таким названием"""
    query = select(Equipment).where(Equipment.name == name)
    if exclude_id:
        query = query.where(Equipment.id != exclude_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_equipment_spec_equipment_exists(
    session: AsyncSession,
    spec_equipment_id: int
) -> bool:
    """Проверить, существует ли тип оборудования"""
    from model.spec_equipment import Spec_Equipment
    query = select(Spec_Equipment).where(Spec_Equipment.id == spec_equipment_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== СОЗДАНИЕ ==========

@timer
async def create_equipment(
    session: AsyncSession,
    equipment_create: EquipmentCreate
) -> Equipment:
    """Создать новое оборудование"""
    equipment = Equipment(**equipment_create.model_dump())
    session.add(equipment)
    await session.commit()
    await session.refresh(equipment)
    return equipment

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_equipment(
    session: AsyncSession,
    equipment_id: int,
    equipment_update: EquipmentUpdate
) -> Optional[Equipment]:
    """Обновить оборудование"""
    equipment = await get_equipment_by_id(session, equipment_id, load_relations=False)
    if not equipment:
        return None

    update_data = equipment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(equipment, field):
            setattr(equipment, field, value)

    await session.commit()
    await session.refresh(equipment)
    return equipment

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_equipment(
    session: AsyncSession,
    equipment_id: int
) -> bool:
    """Удалить оборудование"""
    equipment = await session.get(Equipment, equipment_id)
    if not equipment:
        return False

    await session.delete(equipment)
    await session.commit()
    return True
