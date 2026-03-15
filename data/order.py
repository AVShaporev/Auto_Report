from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import date

from model.order import Order
from schema.order import OrderCreate, OrderUpdate

from utils.timer import timer



# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_by_id(
    session: AsyncSession,
    order_id: int,
    *,
    load_relations: bool = False
) -> Optional[Order]:
    """
    Получить заявку по ID
    
    Args:
        session: Сессия БД
        order_id: ID заявки
        load_relations: Если True, загрузить все связанные данные
    """
    query = select(Order).where(Order.id == order_id)
    
    if load_relations:
        query = query.options(
            selectinload(Order.spec_order),
            selectinload(Order.contract),
            selectinload(Order.object),
            selectinload(Order.user),
            selectinload(Order.report)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_number(
    session: AsyncSession,
    number: str
) -> Optional[Order]:
    """Получить заявку по номеру"""
    query = select(Order).where(Order.number == number)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_user(
    session: AsyncSession,
    user_id: int
) -> List[Order]:
    """Получить все заявки пользователя"""
    query = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Order]:
    """Получить все заявки"""
    query = select(Order).order_by(Order.created_at.desc())
    
    if load_relations:
        query = query.options(
            selectinload(Order.spec_order),
            selectinload(Order.contract),
            selectinload(Order.object),
            selectinload(Order.user)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    spec_order_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    *,
    load_relations: bool = False
) -> Tuple[List[Order], int]:
    """
    Получить список заявок с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Order)
    count_query = select(func.count()).select_from(Order)
    
    # Поиск по номеру и описанию
    if search:
        search_filter = or_(
            Order.number.ilike(f"%{search}%"),
            Order.description.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтры
    if spec_order_id:
        query = query.where(Order.spec_order_id == spec_order_id)
        count_query = count_query.where(Order.spec_order_id == spec_order_id)
    
    if contract_id:
        query = query.where(Order.contract_id == contract_id)
        count_query = count_query.where(Order.contract_id == contract_id)
    
    if object_id:
        query = query.where(Order.object_id == object_id)
        count_query = count_query.where(Order.object_id == object_id)
    
    if user_id:
        query = query.where(Order.user_id == user_id)
        count_query = count_query.where(Order.user_id == user_id)
    
    if status:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)
    
    if date_from:
        query = query.where(Order.created_at >= date_from)
        count_query = count_query.where(Order.created_at >= date_from)
    
    if date_to:
        query = query.where(Order.created_at <= date_to)
        count_query = count_query.where(Order.created_at <= date_to)
    
    # Сортировка
    if sort_by and hasattr(Order, sort_by):
        column = getattr(Order, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Order.created_at.desc())
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Order.spec_order),
            selectinload(Order.contract),
            selectinload(Order.object),
            selectinload(Order.user)
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
async def get_options(
    session: AsyncSession,
    status: Optional[str] = None
) -> List[Order]:
    """
    Получить минимальную информацию о заявках для выпадающих списков
    """
    query = select(Order).order_by(Order.created_at.desc())
    
    if status:
        query = query.where(Order.status == status)
    
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_number_exists(
    session: AsyncSession,
    number: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли заявка с таким номером"""
    query = select(Order).where(Order.number == number)
    if exclude_id:
        query = query.where(Order.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def check_spec_order_exists(
    session: AsyncSession,
    spec_order_id: int
) -> bool:
    """Проверить, существует ли тип заявки"""
    from model.spec_order import Spec_Order
    
    query = select(Spec_Order).where(Spec_Order.id == spec_order_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_contract_exists(
    session: AsyncSession,
    contract_id: int
) -> bool:
    """Проверить, существует ли контракт"""
    from model.contract import Contract
    
    query = select(Contract).where(Contract.id == contract_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_object_exists(
    session: AsyncSession,
    object_id: int
) -> bool:
    """Проверить, существует ли объект"""
    from model.object import Object
    
    query = select(Object).where(Object.id == object_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_user_exists(
    session: AsyncSession,
    user_id: int
) -> bool:
    """Проверить, существует ли пользователь"""
    from model.user import User
    
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_report_exists(
    session: AsyncSession,
    report_id: int
) -> bool:
    """Проверить, существует ли отчет"""
    from model.report import Report
    
    query = select(Report).where(Report.id == report_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_reports(
    session: AsyncSession,
    order_id: int
) -> int:
    """Посчитать количество отчетов по заявке (обычно 0 или 1)"""
    from model.report import Report
    
    query = select(func.count()).select_from(Report).where(
        Report.order_id == order_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== ОБНОВЛЕНИЕ СТАТУСА ==========

@timer
async def update_status(
    session: AsyncSession,
    order_id: int,
    status: str
) -> Optional[Order]:
    """Обновить статус заявки"""
    order = await get_by_id(session, order_id, load_relations=False)
    if not order:
        return None
    
    order.status = status
    await session.commit()
    await session.refresh(order)
    return order

# ========== СОЗДАНИЕ ==========

@timer
async def create(
    session: AsyncSession,
    order_create: OrderCreate,
    user_id: int  # 👈 user_id передается из сервиса
) -> Order:
    """Создать новую заявку"""
    # Создаем словарь с данными и добавляем user_id
    order_data = order_create.dict()
    order_data['user_id'] = user_id
    
    order = Order(**order_data)
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update(
    session: AsyncSession,
    order_id: int,
    order_update: OrderUpdate
) -> Optional[Order]:
    """Обновить заявку"""
    order = await get_by_id(session, order_id, load_relations=False)
    if not order:
        return None
    
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(order, field):
            setattr(order, field, value)
    
    await session.commit()
    await session.refresh(order)
    return order

# ========== УДАЛЕНИЕ ==========

@timer
async def delete(
    session: AsyncSession,
    order_id: int
) -> bool:
    """Удалить заявку"""
    order = await session.get(Order, order_id)
    if not order:
        return False
    
    await session.delete(order)
    await session.commit()
    return True