from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import date, datetime

from model.issue import Issue
from model.objects_equipment import Objects_Equipment
from model.object import Object
from model.user import User
from schema.issue import IssueCreate, IssueUpdate

from utils.timer import timer



# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_issue_by_id(
    session: AsyncSession,
    issue_id: int,
    *,
    load_relations: bool = False
) -> Optional[Issue]:
    """
    Получить неисправность по ID
    
    Args:
        session: Сессия БД
        issue_id: ID неисправности
        load_relations: Если True, загрузить все связанные данные
    """
    query = select(Issue).where(Issue.id == issue_id)
    
    if load_relations:
        # ✅ ИСПРАВЛЕНО: загружаем object_equipment, а не прямые связи
        query = query.options(
            selectinload(Issue.object_equipment)
                .selectinload(Objects_Equipment.object),  # Загружаем объект через связь
            selectinload(Issue.object_equipment)
                .selectinload(Objects_Equipment.equipment),  # Загружаем оборудование через связь
            selectinload(Issue.reported_by),
            selectinload(Issue.assigned_to),
            selectinload(Issue.priority),
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_issue_by_number(
    session: AsyncSession,
    number: str
) -> Optional[Issue]:
    """Получить неисправность по номеру"""
    query = select(Issue).where(Issue.number == number)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_issue_by_object_equipment(
    session: AsyncSession,
    object_equipment_id: int
) -> List[Issue]:
    """Получить все неисправности для конкретной связи объект-оборудование"""
    query = select(Issue).where(
        Issue.object_equipment_id == object_equipment_id
    ).order_by(Issue.detected_date.desc())
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_issue_by_object(
    session: AsyncSession,
    object_id: int
) -> List[Issue]:
    """Получить все неисправности для объекта (через связующую таблицу)"""
    query = (
        select(Issue)
        .join(Objects_Equipment, Objects_Equipment.id == Issue.object_equipment_id)
        .where(Objects_Equipment.object_id == object_id)
        .options(
            selectinload(Issue.object_equipment).selectinload(Objects_Equipment.object),
            selectinload(Issue.object_equipment).selectinload(Objects_Equipment.equipment),
        )
        .order_by(Issue.detected_date.desc())
    )
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_issue_by_equipment(
    session: AsyncSession,
    equipment_id: int
) -> List[Issue]:
    """Получить все неисправности для оборудования (через связующую таблицу)"""
    query = (
        select(Issue)
        .join(Objects_Equipment, Objects_Equipment.id == Issue.object_equipment_id)
        .where(Objects_Equipment.equipment_id == equipment_id)
        .options(
            selectinload(Issue.object_equipment).selectinload(Objects_Equipment.object),
            selectinload(Issue.object_equipment).selectinload(Objects_Equipment.equipment),
        )
        .order_by(Issue.detected_date.desc())
    )
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_issue_by_reporter(
    session: AsyncSession,
    user_id: int
) -> List[Issue]:
    """Получить все неисправности, сообщенные пользователем"""
    query = select(Issue).where(Issue.reported_by_id == user_id).order_by(Issue.detected_date.desc())
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_issue_by_assignee(
    session: AsyncSession,
    user_id: int
) -> List[Issue]:
    """Получить все неисправности, назначенные пользователю"""
    query = select(Issue).where(Issue.assigned_to_id == user_id).order_by(Issue.detected_date.desc())
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_issue_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Issue]:
    """Получить все неисправности"""
    query = select(Issue).order_by(Issue.detected_date.desc())
    
    if load_relations:
        # ✅ ИСПРАВЛЕНО: загружаем через object_equipment
        query = query.options(
            selectinload(Issue.object_equipment)
                .selectinload(Objects_Equipment.object),
            selectinload(Issue.object_equipment)
                .selectinload(Objects_Equipment.equipment),
            selectinload(Issue.reported_by),
            selectinload(Issue.assigned_to)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_issue_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    object_id: Optional[int] = None,
    equipment_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    object_equipment_id: Optional[int] = None,
    status_id: Optional[int] = None,
    priority_id: Optional[int] = None,
    is_resolved: Optional[bool] = None,
    is_critical: Optional[bool] = None,
    reported_by_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "detected_date",
    sort_order: str = "desc",
    *,
    load_relations: bool = False
) -> Tuple[List[Issue], int]:
    """
    Получить список неисправностей с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Issue)
    count_query = select(func.count()).select_from(Issue)
    
    # Поиск по номеру и заголовку
    if search:
        search_filter = or_(
            Issue.number.ilike(f"%{search}%"),
            Issue.title.ilike(f"%{search}%"),
            Issue.description.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтры
    if object_equipment_id:
        query = query.where(Issue.object_equipment_id == object_equipment_id)
        count_query = count_query.where(Issue.object_equipment_id == object_equipment_id)
    
    if status_id:
        query = query.where(Issue.status_id == status_id)
        count_query = count_query.where(Issue.status_id == status_id)

    if priority_id:
        query = query.where(Issue.priority_id == priority_id)
        count_query = count_query.where(Issue.priority_id == priority_id)
    
    if is_resolved is not None:
        query = query.where(Issue.is_resolved == is_resolved)
        count_query = count_query.where(Issue.is_resolved == is_resolved)
    
    if is_critical is not None:
        query = query.where(Issue.is_critical == is_critical)
        count_query = count_query.where(Issue.is_critical == is_critical)
    
    if reported_by_id:
        query = query.where(Issue.reported_by_id == reported_by_id)
        count_query = count_query.where(Issue.reported_by_id == reported_by_id)
    
    if assigned_to_id:
        query = query.where(Issue.assigned_to_id == assigned_to_id)
        count_query = count_query.where(Issue.assigned_to_id == assigned_to_id)
    
    if date_from:
        query = query.where(Issue.detected_date >= date_from)
        count_query = count_query.where(Issue.detected_date >= date_from)
    
    if date_to:
        query = query.where(Issue.detected_date <= date_to)
        count_query = count_query.where(Issue.detected_date <= date_to)
    
    # Фильтры через связующую таблицу
    if object_id or equipment_id or contract_id:
        query = query.join(
            Objects_Equipment,
            Objects_Equipment.id == Issue.object_equipment_id
        )
        count_query = count_query.join(
            Objects_Equipment,
            Objects_Equipment.id == Issue.object_equipment_id
        )

        if object_id:
            query = query.where(Objects_Equipment.object_id == object_id)
            count_query = count_query.where(Objects_Equipment.object_id == object_id)

        if equipment_id:
            query = query.where(Objects_Equipment.equipment_id == equipment_id)
            count_query = count_query.where(Objects_Equipment.equipment_id == equipment_id)

        if contract_id:
            # Issue → Objects_Equipment → Object → contract_id
            query = query.join(Object, Object.id == Objects_Equipment.object_id)
            count_query = count_query.join(Object, Object.id == Objects_Equipment.object_id)
            query = query.where(Object.contract_id == contract_id)
            count_query = count_query.where(Object.contract_id == contract_id)
    
    # Сортировка
    if sort_by and hasattr(Issue, sort_by):
        column = getattr(Issue, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Issue.detected_date.desc())
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        # ✅ ИСПРАВЛЕНО: загружаем через object_equipment
        query = query.options(
            selectinload(Issue.object_equipment)
                .selectinload(Objects_Equipment.object),
            selectinload(Issue.object_equipment)
                .selectinload(Objects_Equipment.equipment),
            selectinload(Issue.reported_by),
            selectinload(Issue.assigned_to)
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
async def get_issue_options(
    session: AsyncSession,
    status_id: Optional[int] = None,
    is_resolved: Optional[bool] = None
) -> List[Issue]:
    """
    Получить минимальную информацию о неисправностях для выпадающих списков
    """
    query = select(Issue).order_by(Issue.detected_date.desc())

    if status_id:
        query = query.where(Issue.status_id == status_id)

    if is_resolved is not None:
        query = query.where(Issue.is_resolved == is_resolved)
    
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_issue_number_exists(
    session: AsyncSession,
    number: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли неисправность с таким номером"""
    query = select(Issue).where(Issue.number == number)
    if exclude_id:
        query = query.where(Issue.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def check_issue_object_equipment_exists(
    session: AsyncSession,
    object_equipment_id: int
) -> bool:
    """Проверить, существует ли связь объекта с оборудованием"""
    query = select(Objects_Equipment).where(Objects_Equipment.id == object_equipment_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_issue_user_exists(
    session: AsyncSession,
    user_id: int
) -> bool:
    """Проверить, существует ли пользователь с указанным ID"""
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_issue_by_object(
    session: AsyncSession,
    object_id: int,
    resolved: Optional[bool] = None
) -> int:
    """Посчитать количество неисправностей по объекту"""
    query = select(func.count()).select_from(Issue).join(
        Objects_Equipment,
        Objects_Equipment.id == Issue.object_equipment_id
    ).where(Objects_Equipment.object_id == object_id)
    
    if resolved is not None:
        query = query.where(Issue.is_resolved == resolved)
    
    result = await session.execute(query)
    return result.scalar() or 0

@timer
async def count_issue_by_equipment(
    session: AsyncSession,
    equipment_id: int,
    resolved: Optional[bool] = None
) -> int:
    """Посчитать количество неисправностей по оборудованию"""
    query = select(func.count()).select_from(Issue).join(
        Objects_Equipment,
        Objects_Equipment.id == Issue.object_equipment_id
    ).where(Objects_Equipment.equipment_id == equipment_id)
    
    if resolved is not None:
        query = query.where(Issue.is_resolved == resolved)
    
    result = await session.execute(query)
    return result.scalar() or 0

# ========== ОБНОВЛЕНИЕ СТАТУСА ==========

@timer
async def update_issue_status(
    session: AsyncSession,
    issue_id: int,
    status_id: int,
    resolved_date: Optional[date] = None
) -> Optional[Issue]:
    """Обновить статус неисправности"""
    from model.spec_status import Spec_Status

    issue = await get_issue_by_id(session, issue_id, load_relations=False)
    if not issue:
        return None

    new_status = await session.get(Spec_Status, status_id)
    if not new_status:
        return None

    issue.status_id = status_id
    issue.is_resolved = new_status.code in ('resolved', 'closed')

    if new_status.code == 'resolved' and resolved_date:
        issue.resolved_date = resolved_date

    await session.commit()
    await session.refresh(issue)
    return issue

# ========== СОЗДАНИЕ ==========

@timer
async def create_issue(
    session: AsyncSession,
    issue_create: IssueCreate,
    reported_by_id: int,
    status_id: int,
    *,
    number: str,
) -> Issue:
    """Создать новую неисправность. `number` генерится в сервисе."""
    issue_data = issue_create.dict()
    issue_data['number'] = number
    issue_data['reported_by_id'] = reported_by_id
    issue_data['status_id'] = status_id
    issue_data['is_resolved'] = False

    issue = Issue(**issue_data)
    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return issue

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_issue(
    session: AsyncSession,
    issue_id: int,
    issue_update: IssueUpdate
) -> Optional[Issue]:
    """Обновить неисправность"""
    issue = await get_issue_by_id(session, issue_id, load_relations=False)
    if not issue:
        return None
    
    update_data = issue_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(issue, field):
            setattr(issue, field, value)
    
    await session.commit()
    await session.refresh(issue)
    return issue

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_issue(
    session: AsyncSession,
    issue_id: int
) -> bool:
    """Удалить неисправность"""
    issue = await session.get(Issue, issue_id)
    if not issue:
        return False
    
    await session.delete(issue)
    await session.commit()
    return True