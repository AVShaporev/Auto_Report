from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload, raiseload
from typing import Optional, List, Tuple
from datetime import date

from model.order import Order
from model.object import Object
from schema.order import OrderCreate, OrderUpdate
from data import spec_order_status as spec_order_status_data

from utils.timer import timer
from utils.loading import shallow_load



# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_order_by_id(
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
            selectinload(Order.report),
            selectinload(Order.spec_order_status),
        )

    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_order_by_number(
    session: AsyncSession,
    number: str
) -> Optional[Order]:
    """Получить заявку по номеру"""
    query = select(Order).where(Order.number == number)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_order_by_user(
    session: AsyncSession,
    user_id: int
) -> List[Order]:
    """Получить все заявки пользователя"""
    query = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_order_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Order]:
    """Получить все заявки"""
    query = select(Order).order_by(Order.created_at.desc())

    if load_relations:
        query = query.options(
            *shallow_load(
                Order.spec_order,
                Order.contract,
                Order.object,
                Order.user,
            ),
            raiseload(Order.report),
        )

    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_order_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    spec_order_id: Optional[List[int]] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    status_id: Optional[List[int]] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    region_id: Optional[List[int]] = None,
    arial_id: Optional[List[int]] = None,
    locality_id: Optional[List[int]] = None,
    street_id: Optional[List[int]] = None,
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
        # Список id'шников типов заявок — IN, чтобы поддержать multi-select на фронте.
        query = query.where(Order.spec_order_id.in_(spec_order_id))
        count_query = count_query.where(Order.spec_order_id.in_(spec_order_id))

    if contract_id:
        query = query.where(Order.contract_id == contract_id)
        count_query = count_query.where(Order.contract_id == contract_id)

    if object_id:
        query = query.where(Order.object_id == object_id)
        count_query = count_query.where(Order.object_id == object_id)

    if user_id:
        query = query.where(Order.user_id == user_id)
        count_query = count_query.where(Order.user_id == user_id)

    if assigned_to_id is not None:
        # 0 → «без ответственного» (NULL), иначе точное совпадение.
        if assigned_to_id == 0:
            query = query.where(Order.assigned_to_id.is_(None))
            count_query = count_query.where(Order.assigned_to_id.is_(None))
        else:
            query = query.where(Order.assigned_to_id == assigned_to_id)
            count_query = count_query.where(Order.assigned_to_id == assigned_to_id)

    if status_id:
        # Мультиселект по id справочника — фильтруем по FK напрямую, без JOIN.
        query = query.where(Order.status_id.in_(status_id))
        count_query = count_query.where(Order.status_id.in_(status_id))

    if date_from:
        query = query.where(Order.created_at >= date_from)
        count_query = count_query.where(Order.created_at >= date_from)

    if date_to:
        query = query.where(Order.created_at <= date_to)
        count_query = count_query.where(Order.created_at <= date_to)

    # Фильтры по адресу объекта заявки (через JOIN с objects).
    # Каждый фильтр — список id; внутри одного фильтра OR (IN), между фильтрами AND.
    address_filters = (region_id, arial_id, locality_id, street_id)
    if any(f for f in address_filters):
        query = query.join(Object, Order.object_id == Object.id)
        count_query = count_query.join(Object, Order.object_id == Object.id)
        if region_id:
            query = query.where(Object.region_id.in_(region_id))
            count_query = count_query.where(Object.region_id.in_(region_id))
        if arial_id:
            query = query.where(Object.arial_id.in_(arial_id))
            count_query = count_query.where(Object.arial_id.in_(arial_id))
        if locality_id:
            query = query.where(Object.locality_id.in_(locality_id))
            count_query = count_query.where(Object.locality_id.in_(locality_id))
        if street_id:
            query = query.where(Object.street_id.in_(street_id))
            count_query = count_query.where(Object.street_id.in_(street_id))

    # Сортировка
    if sort_by and hasattr(Order, sort_by):
        column = getattr(Order, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Order.created_at.desc())

    # Загрузка связанных данных (если запрошено).
    # `shallow_load` отрубает каскад «contract→customer→spec_arial→…», который
    # на модели по-умолчанию помечен `lazy="selectin/joined"` и взрывал список
    # заявок до 400 SQL-запросов на /order/list. См. utils/loading.py.
    if load_relations:
        query = query.options(
            *shallow_load(
                Order.spec_order,
                Order.contract,
                Order.object,
                Order.user,
            ),
            # report тоже помечен на модели lazy="selectin" — отрубаем
            raiseload(Order.report),
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
async def get_order_options(
    session: AsyncSession,
    status_id: Optional[int] = None
) -> List[Order]:
    """
    Получить минимальную информацию о заявках для выпадающих списков
    """
    query = select(Order).order_by(Order.created_at.desc())

    if status_id:
        query = query.where(Order.status_id == status_id)

    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_order_number_exists(
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
async def count_reports_by_order(
    session: AsyncSession,
    order_id: int
) -> int:
    """Посчитать количество отчётов по заявке (1:1 — всегда 0 или 1)."""
    query = select(func.count()).select_from(Order).where(
        Order.id == order_id,
        Order.report_id.isnot(None),
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== ОБНОВЛЕНИЕ СТАТУСА ==========

@timer
async def update_order_status(
    session: AsyncSession,
    order_id: int,
    status_id: int
) -> Optional[Order]:
    """Обновить статус заявки. Принимает FK id из spec_order_statuses.

    Валидация «есть ли такой id» — на уровне DB (FK constraint), 400 сюда
    не долетит; при попытке несуществующего id INSERT/UPDATE упадёт с
    ForeignKeyViolation.
    """
    order = await get_order_by_id(session, order_id, load_relations=False)
    if not order:
        return None

    order.status_id = status_id
    await session.commit()
    await session.refresh(order)
    return order

# ========== СОЗДАНИЕ ==========

@timer
async def create_order(
    session: AsyncSession,
    order_create: OrderCreate,
    user_id: int,
    *,
    number: str,
) -> Order:
    """Создать новую заявку. number и user_id приходят из сервиса.

    Если OrderCreate.status_id не задан — берём дефолтный
    (spec_order_statuses.is_default=true).
    """
    order_data = order_create.model_dump()
    order_data['user_id'] = user_id
    order_data['number'] = number

    if not order_data.get('status_id'):
        order_data['status_id'] = await spec_order_status_data.get_default_status_id(session)

    order = Order(**order_data)
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_order(
    session: AsyncSession,
    order_id: int,
    order_update: OrderUpdate
) -> Optional[Order]:
    """Обновить заявку.

    OrderUpdate.status_id — если передан, обновляется как обычное FK-поле.
    """
    order = await get_order_by_id(session, order_id, load_relations=False)
    if not order:
        return None

    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(order, field):
            setattr(order, field, value)

    await session.commit()
    await session.refresh(order)
    return order

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_order(
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
