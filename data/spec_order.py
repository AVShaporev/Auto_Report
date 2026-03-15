from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_order import Spec_Order
from schema.spec_order import SpecOrderCreate, SpecOrderUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_by_id(
    session: AsyncSession,
    spec_order_id: int,
    *,
    load_orders: bool = False
) -> Optional[Spec_Order]:
    """
    Получить тип заявки по ID
    
    Args:
        session: Сессия БД
        spec_order_id: ID типа заявки
        load_orders: Если True, загрузить связанные заявки
    """
    query = select(Spec_Order).where(Spec_Order.id == spec_order_id)
    
    if load_orders:
        query = query.options(selectinload(Spec_Order.orders))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Order]:
    """Получить тип заявки по названию"""
    query = select(Spec_Order).where(Spec_Order.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_all(
    session: AsyncSession,
    *,
    load_orders: bool = False
) -> List[Spec_Order]:
    """Получить все типы заявок"""
    query = select(Spec_Order).order_by(Spec_Order.name)
    
    if load_orders:
        query = query.options(selectinload(Spec_Order.orders))
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_orders: bool = False
) -> Tuple[List[Spec_Order], int]:
    """
    Получить список типов заявок с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Order)
    count_query = select(func.count()).select_from(Spec_Order)
    
    # Поиск по названию и краткому наименованию
    if search:
        search_filter = or_(
            Spec_Order.name.ilike(f"%{search}%"),
            Spec_Order.short_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Order, sort_by):
        column = getattr(Spec_Order, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Order.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_orders:
        query = query.options(selectinload(Spec_Order.orders))
    
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
async def get_options(
    session: AsyncSession
) -> List[Spec_Order]:
    """
    Получить минимальную информацию о типах заявок для выпадающих списков
    """
    query = select(Spec_Order).order_by(Spec_Order.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли тип заявки с таким названием"""
    query = select(Spec_Order).where(Spec_Order.name == name)
    if exclude_id:
        query = query.where(Spec_Order.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_orders(
    session: AsyncSession,
    spec_order_id: int
) -> int:
    """
    Посчитать количество заявок данного типа
    
    Это эффективнее, чем загружать все объекты через relationship
    """
    from model.order import Order
    
    query = select(func.count()).select_from(Order).where(
        Order.spec_order_id == spec_order_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

@timer
async def create(
    session: AsyncSession,
    spec_order_create: SpecOrderCreate
) -> Spec_Order:
    """Создать новый тип заявки"""
    spec_order = Spec_Order(**spec_order_create.dict())
    session.add(spec_order)
    await session.commit()
    await session.refresh(spec_order)
    return spec_order

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update(
    session: AsyncSession,
    spec_order_id: int,
    spec_order_update: SpecOrderUpdate
) -> Optional[Spec_Order]:
    """Обновить тип заявки"""
    spec_order = await get_by_id(session, spec_order_id, load_orders=False)
    if not spec_order:
        return None
    
    update_data = spec_order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_order, field):
            setattr(spec_order, field, value)
    
    await session.commit()
    await session.refresh(spec_order)
    return spec_order

# ========== УДАЛЕНИЕ ==========

@timer
async def delete(
    session: AsyncSession,
    spec_order_id: int
) -> bool:
    """Удалить тип заявки"""
    spec_order = await session.get(Spec_Order, spec_order_id)
    if not spec_order:
        return False
    
    await session.delete(spec_order)
    await session.commit()
    return True