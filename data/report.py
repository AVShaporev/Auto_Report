from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload, raiseload
from typing import Optional, List, Tuple
from datetime import date

from model.report import Report
from model.period import Period
from model.contract import Contract
from model.object import Object
from model.user import User
from model.order import Order
from model.spec_report_status import Spec_Report_Status
from schema.report import ReportCreate, ReportUpdate

from utils.timer import timer
from utils.loading import shallow_load


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_report_by_id(
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
            selectinload(Report.order),
            selectinload(Report.status),
        )

    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_report_by_number(
    session: AsyncSession,
    number: str
) -> Optional[Report]:
    """Получить отчет по номеру"""
    query = select(Report).where(Report.number == number)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_report_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Report]:
    """Получить все отчеты"""
    query = select(Report).order_by(Report.created_at.desc())

    if load_relations:
        query = query.options(
            *shallow_load(
                Report.period,
                Report.contract,
                Report.object,
                Report.user,
                Report.status,
            ),
            # фантомные auto-selectin, не нужные в списке
            raiseload(Report.attachments),
            raiseload(Report.order),
        )

    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_report_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    period_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status_id: Optional[int] = None,
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

    if status_id is not None:
        query = query.where(Report.status_id == status_id)
        count_query = count_query.where(Report.status_id == status_id)

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

    # Загрузка связанных данных (если запрошено).
    # Без shallow_load — каждый Report тянул бы spec_status + period + contract +
    # object + user + order, а внутри ещё всё, что у этих моделей помечено
    # lazy="selectin/joined". На 100 записях это сотни SQL-запросов.
    if load_relations:
        query = query.options(
            *shallow_load(
                Report.period,
                Report.contract,
                Report.object,
                Report.user,
                Report.order,
                Report.status,
            ),
            raiseload(Report.attachments),
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
async def get_report_options(
    session: AsyncSession,
    status_id: Optional[int] = None
) -> List[Report]:
    """
    Получить минимальную информацию об отчетах для выпадающих списков
    """
    query = (
        select(Report)
        .options(selectinload(Report.status))
        .order_by(Report.created_at.desc())
    )

    if status_id is not None:
        query = query.where(Report.status_id == status_id)

    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_report_number_exists(
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
async def count_orders_by_report(
    session: AsyncSession,
    report_id: int
) -> int:
    """Посчитать количество заявок по отчету (обычно 0 или 1)"""
    query = select(func.count()).select_from(Order).where(
        Order.report_id == report_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СМЕНА СТАТУСА ==========

@timer
async def update_report_status(
    session: AsyncSession,
    report_id: int,
    status_id: int,
) -> Optional[Report]:
    """Установить статус отчёта (FK на spec_report_statuses)."""
    report = await get_report_by_id(session, report_id, load_relations=False)
    if not report:
        return None

    report.status_id = status_id
    await session.commit()
    await session.refresh(report)
    return report


@timer
async def get_default_spec_report_status(
    session: AsyncSession,
) -> Optional[Spec_Report_Status]:
    """Вспомогательное: дефолтный статус отчёта (is_default = true).

    После миграции f3a4b5c6d7e8 это «В работе». Partial unique index
    гарантирует ровно одну такую строку.
    """
    query = select(Spec_Report_Status).where(Spec_Report_Status.is_default == True)  # noqa: E712
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_report_status_by_name(
    session: AsyncSession,
    name: str,
) -> Optional[Spec_Report_Status]:
    """Найти статус отчёта по name."""
    query = select(Spec_Report_Status).where(Spec_Report_Status.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()


# ========== СОЗДАНИЕ ==========

@timer
async def create_report(
    session: AsyncSession,
    report_create: ReportCreate,
    user_id: int,
    number: str,
    order: Order,
    status_id: int,
) -> Report:
    """Создать новый отчет и атомарно привязать его к заявке (1:1)."""
    report_data = report_create.model_dump()
    report_data.pop('report_period', None)
    report_data.pop('order_id', None)  # связь хранится в orders.report_id
    report_data['user_id'] = user_id
    report_data['number'] = number
    report_data['status_id'] = status_id

    report = Report(**report_data)
    session.add(report)
    await session.flush()  # получаем report.id, не закрывая транзакцию
    order.report_id = report.id
    await session.commit()
    await session.refresh(report)
    return report

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_report(
    session: AsyncSession,
    report_id: int,
    report_update: ReportUpdate
) -> Optional[Report]:
    """Обновить отчет"""
    report = await get_report_by_id(session, report_id, load_relations=False)
    if not report:
        return None

    update_data = report_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(report, field):
            setattr(report, field, value)

    await session.commit()
    await session.refresh(report)
    return report

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_report(
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
