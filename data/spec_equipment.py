from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_equipment import Spec_Equipment
from schema.spec_equipment import SpecEquipmentCreate, SpecEquipmentUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_spec_equipment_by_id(
                                    session: AsyncSession,
                                    spec_equipment_id: int,
                                    *,
                                    load_equipments: bool = False
                                    ) -> Optional[Spec_Equipment]:
    """
    Получить тип оборудования по ID
    
    Args:
        session: Сессия БД
        spec_equipment_id: ID типа оборудования
        load_equipments: Если True, загрузить связанное оборудование
    """
    query = select(Spec_Equipment).where(Spec_Equipment.id == spec_equipment_id)
    
    if load_equipments:
        query = query.options(selectinload(Spec_Equipment.equipments))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_spec_equipment_by_name(
                                    session: AsyncSession,
                                    name: str
                                    ) -> Optional[Spec_Equipment]:
    """Получить тип оборудования по названию"""
    query = select(Spec_Equipment).where(Spec_Equipment.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_spec_equipment_all(
                                session: AsyncSession,
                                *,
                                load_equipments: bool = False
                                ) -> List[Spec_Equipment]:
    """Получить все типы оборудования"""
    query = select(Spec_Equipment).order_by(Spec_Equipment.name)
    
    if load_equipments:
        query = query.options(selectinload(Spec_Equipment.equipments))
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_spec_equipment_paginated(
                                        session: AsyncSession,
                                        skip: int = 0,
                                        limit: int = 20,
                                        search: Optional[str] = None,
                                        sort_by: str = "name",
                                        sort_order: str = "asc",
                                        *,
                                        load_equipments: bool = False
                                    ) -> Tuple[List[Spec_Equipment], int]:
    """
    Получить список типов оборудования с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Equipment)
    count_query = select(func.count()).select_from(Spec_Equipment)
    
    # Поиск по названию
    if search:
        search_filter = Spec_Equipment.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Equipment, sort_by):
        column = getattr(Spec_Equipment, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Equipment.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_equipments:
        query = query.options(selectinload(Spec_Equipment.equipments))
    
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
async def get_spec_equipment_options(
                                    session: AsyncSession
                                    ) -> List[Spec_Equipment]:
    """
    Получить минимальную информацию о типах оборудования для выпадающих списков
    """
    query = select(Spec_Equipment).order_by(Spec_Equipment.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_spec_equipment_name_exists(
                                            session: AsyncSession,
                                            name: str,
                                            exclude_id: Optional[int] = None
                                            ) -> bool:
    """Проверить, существует ли тип оборудования с таким названием"""
    query = select(Spec_Equipment).where(Spec_Equipment.name == name)
    if exclude_id:
        query = query.where(Spec_Equipment.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_spec_equipment_equipments(
                                            session: AsyncSession,
                                            spec_equipment_id: int
                                            ) -> int:
    """
    Посчитать количество оборудования данного типа
    
    Это эффективнее, чем загружать все объекты через relationship
    """
    from model.equipment import Equipment
    
    query = select(func.count()).select_from(Equipment).where(
        Equipment.spec_equipment_id == spec_equipment_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

@timer
async def create_spec_equipment(
                                session: AsyncSession,
                                spec_equipment_create: SpecEquipmentCreate
                                ) -> Spec_Equipment:
    """Создать новый тип оборудования"""
    spec_equipment = Spec_Equipment(**spec_equipment_create.dict())
    session.add(spec_equipment)
    await session.commit()
    await session.refresh(spec_equipment)
    return spec_equipment

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_spec_equipment(
                                session: AsyncSession,
                                spec_equipment_id: int,
                                spec_equipment_update: SpecEquipmentUpdate
                                ) -> Optional[Spec_Equipment]:
    """Обновить тип оборудования"""
    spec_equipment = await get_by_id(session, spec_equipment_id, load_equipments=False)
    if not spec_equipment:
        return None
    
    update_data = spec_equipment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_equipment, field):
            setattr(spec_equipment, field, value)
    
    await session.commit()
    await session.refresh(spec_equipment)
    return spec_equipment

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_spec_equipment(
                                session: AsyncSession,
                                spec_equipment_id: int
                                ) -> bool:
    """Удалить тип оборудования"""
    spec_equipment = await session.get(Spec_Equipment, spec_equipment_id)
    if not spec_equipment:
        return False
    
    await session.delete(spec_equipment)
    await session.commit()
    return True