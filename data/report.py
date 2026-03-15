from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import date

from model.report import Report
from model.period import Period
from model.contract import Contract
from model.object import Object
from model.user import User
from model.order import Order
from schema.report import ReportCreate, ReportUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_by_id(
    session: AsyncSession,
    report_id: int,
    *,
    load_relations: bool = False
) -> Optional[Report]:
    """
    Получить отчет по ID
    
    Args:
        session: Сессия БД
        report_id: ID отчета
        load_relations: Если True, загрузить все связанные данные
    """
    query = select(Report).where(Report.id == report_id)
    
    if load_relations:
        query = query.options(
            selectinload(Report.period),
            selectinload(Report.contract),
            selectinload(Report.object),
            selectinload(Report.user),
            selectinload(Report.order)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_number(
    session: AsyncSession,
    number: str
) -> Optional[Report]:
    """Получить отчет по номеру"""
    query = select(Report).where(Report.number == number)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Report]:
    """Получить все отчеты"""
    query = select(Report).order_by(Report.created_at.desc())
    
    if load_relations:
        query = query.options(
            selectinload(Report.period),
            selectinload(Report.contract),
            selectinload(Report.object),
            selectinload(Report.user)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    period_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    check_pass: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    *,
    load_relations: bool = False
) -> Tuple[List[Report], int]:
    """
    Получить список отчетов с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Report)
    count_query = select(func.count()).select_from(Report)
    
    # Поиск по номеру и описанию
    if search:
        search_filter = or_(
            Report.number.ilike(f"%{search}%"),
            Report.description.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтры
    if period_id:
        query = query.where(Report.period_id == period_id)
        count_query = count_query.where(Report.period_id == period_id)
    
    if contract_id:
        query = query.where(Report.contract_id == contract_id)
        count_query = count_query.where(Report.contract_id == contract_id)
    
    if object_id:
        query = query.where(Report.object_id == object_id)
        count_query = count_query.where(Report.object_id == object_id)
    
    if user_id:
        query = query.where(Report.user_id == user_id)
        count_query = count_query.where(Report.user_id == user_id)
    
    if check_pass is not None:
        query = query.where(Report.check_pass == check_pass)
        count_query = count_query.where(Report.check_pass == check_pass)
    
    if date_from:
        query = query.where(Report.created_at >= date_from)
        count_query = count_query.where(Report.created_at >= date_from)
    
    if date_to:
        query = query.where(Report.created_at <= date_to)
        count_query = count_query.where(Report.created_at <= date_to)
    
    # Сортировка
    if sort_by and hasattr(Report, sort_by):
        column = getattr(Report, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Report.created_at.desc())
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Report.period),
            selectinload(Report.contract),
            selectinload(Report.object),
            selectinload(Report.user)
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
    check_pass: Optional[bool] = None
) -> List[Report]:
    """
    Получить минимальную информацию об отчетах для выпадающих списков
    """
    query = select(Report).order_by(Report.created_at.desc())
    
    if check_pass is not None:
        query = query.where(Report.check_pass == check_pass)
    
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_number_exists(
    session: AsyncSession,
    number: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли отчет с таким номером"""
    query = select(Report).where(Report.number == number)
    if exclude_id:
        query = query.where(Report.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def check_period_exists(
    session: AsyncSession,
    period_id: int
) -> bool:
    """Проверить, существует ли период"""
    query = select(Period).where(Period.id == period_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_contract_exists(
    session: AsyncSession,
    contract_id: int
) -> bool:
    """Проверить, существует ли контракт"""
    query = select(Contract).where(Contract.id == contract_id)
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
async def check_user_exists(
    session: AsyncSession,
    user_id: int
) -> bool:
    """Проверить, существует ли пользователь"""
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_orders(
    session: AsyncSession,
    report_id: int
) -> int:
    """Посчитать количество заявок по отчету (обычно 0 или 1)"""
    query = select(func.count()).select_from(Order).where(
        Order.report_id == report_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== УТВЕРЖДЕНИЕ ОТЧЕТА ==========

@timer
async def approve(
    session: AsyncSession,
    report_id: int,
    check_pass: bool = True
) -> Optional[Report]:
    """Утвердить или отклонить отчет"""
    report = await get_by_id(session, report_id, load_relations=False)
    if not report:
        return None
    
    report.check_pass = check_pass
    await session.commit()
    await session.refresh(report)
    return report

# ========== СОЗДАНИЕ ==========

@timer
async def create(
    session: AsyncSession,
    report_create: ReportCreate,
    user_id: int  # 👈 user_id передается из сервиса
) -> Report:
    """Создать новый отчет"""
    # Создаем словарь с данными и добавляем user_id
    report_data = report_create.dict()
    report_data['user_id'] = user_id
    report_data['check_pass'] = False  # Новый отчет всегда не утвержден
    
    report = Report(**report_data)
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update(
    session: AsyncSession,
    report_id: int,
    report_update: ReportUpdate
) -> Optional[Report]:
    """Обновить отчет"""
    report = await get_by_id(session, report_id, load_relations=False)
    if not report:
        return None
    
    update_data = report_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(report, field):
            setattr(report, field, value)
    
    await session.commit()
    await session.refresh(report)
    return report

# ========== УДАЛЕНИЕ ==========

@timer
async def delete(
    session: AsyncSession,
    report_id: int
) -> bool:
    """Удалить отчет"""
    report = await session.get(Report, report_id)
    if not report:
        return False
    
    await session.delete(report)
    await session.commit()
    return True