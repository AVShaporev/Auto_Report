from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.object import Object
from schema.object import ObjectCreate, ObjectUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    object_id: int,
    *,
    load_relations: bool = False
) -> Optional[Object]:
    """
    Получить объект по ID
    
    Args:
        session: Сессия БД
        object_id: ID объекта
        load_relations: Если True, загрузить все связанные данные
    """
    query = select(Object).where(Object.id == object_id)
    
    if load_relations:
        query = query.options(
            selectinload(Object.region),
            selectinload(Object.arial),
            selectinload(Object.locality),
            selectinload(Object.street),
            selectinload(Object.spec_build),
            selectinload(Object.spec_room),
            selectinload(Object.period),
            selectinload(Object.contract),
            selectinload(Object.objects_equipments),
            selectinload(Object.reports),
            selectinload(Object.orders)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Object]:
    """Получить объект по названию"""
    query = select(Object).where(Object.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Object]:
    """Получить все объекты"""
    query = select(Object).order_by(Object.name)
    
    if load_relations:
        query = query.options(
            selectinload(Object.region),
            selectinload(Object.arial),
            selectinload(Object.locality),
            selectinload(Object.street),
            selectinload(Object.contract)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    region_id: Optional[int] = None,
    arial_id: Optional[int] = None,
    locality_id: Optional[int] = None,
    street_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    period_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_relations: bool = False
) -> Tuple[List[Object], int]:
    """
    Получить список объектов с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Object)
    count_query = select(func.count()).select_from(Object)
    
    # Поиск по названию
    if search:
        search_filter = or_(
            Object.name.ilike(f"%{search}%"),
            Object.responsible_face.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтры
    if region_id:
        query = query.where(Object.region_id == region_id)
        count_query = count_query.where(Object.region_id == region_id)
    
    if arial_id:
        query = query.where(Object.arial_id == arial_id)
        count_query = count_query.where(Object.arial_id == arial_id)
    
    if locality_id:
        query = query.where(Object.locality_id == locality_id)
        count_query = count_query.where(Object.locality_id == locality_id)
    
    if street_id:
        query = query.where(Object.street_id == street_id)
        count_query = count_query.where(Object.street_id == street_id)
    
    if contract_id:
        query = query.where(Object.contract_id == contract_id)
        count_query = count_query.where(Object.contract_id == contract_id)
    
    if period_id:
        query = query.where(Object.period_id == period_id)
        count_query = count_query.where(Object.period_id == period_id)
    
    # Сортировка
    if sort_by and hasattr(Object, sort_by):
        column = getattr(Object, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Object.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Object.region),
            selectinload(Object.arial),
            selectinload(Object.locality),
            selectinload(Object.street),
            selectinload(Object.contract)
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
) -> List[Object]:
    """
    Получить минимальную информацию об объектах для выпадающих списков
    """
    query = select(Object).order_by(Object.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ СВЯЗАННЫХ ОБЪЕКТОВ ==========

async def check_region_exists(
    session: AsyncSession,
    region_id: int
) -> bool:
    """Проверить, существует ли регион"""
    from model.region import Region
    
    query = select(Region).where(Region.id == region_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_arial_exists(
    session: AsyncSession,
    arial_id: int
) -> bool:
    """Проверить, существует ли район"""
    from model.arial import Arial
    
    query = select(Arial).where(Arial.id == arial_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_locality_exists(
    session: AsyncSession,
    locality_id: int
) -> bool:
    """Проверить, существует ли населенный пункт"""
    from model.locality import Locality
    
    query = select(Locality).where(Locality.id == locality_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_street_exists(
    session: AsyncSession,
    street_id: int
) -> bool:
    """Проверить, существует ли улица"""
    from model.street import Street
    
    query = select(Street).where(Street.id == street_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_spec_build_exists(
    session: AsyncSession,
    spec_build_id: int
) -> bool:
    """Проверить, существует ли тип строения"""
    from model.spec_build import Spec_Build
    
    query = select(Spec_Build).where(Spec_Build.id == spec_build_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_spec_room_exists(
    session: AsyncSession,
    spec_room_id: int
) -> bool:
    """Проверить, существует ли тип помещения"""
    from model.spec_room import Spec_Room
    
    query = select(Spec_Room).where(Spec_Room.id == spec_room_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_period_exists(
    session: AsyncSession,
    period_id: int
) -> bool:
    """Проверить, существует ли период"""
    from model.period import Period
    
    query = select(Period).where(Period.id == period_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_contract_exists(
    session: AsyncSession,
    contract_id: int
) -> bool:
    """Проверить, существует ли контракт"""
    from model.contract import Contract
    
    query = select(Contract).where(Contract.id == contract_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

async def count_equipments(
    session: AsyncSession,
    object_id: int
) -> int:
    """Посчитать количество оборудования на объекте"""
    from model.objects_equipment import Objects_Equipment
    
    query = select(func.count()).select_from(Objects_Equipment).where(
        Objects_Equipment.object_id == object_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

async def count_reports(
    session: AsyncSession,
    object_id: int
) -> int:
    """Посчитать количество отчетов по объекту"""
    from model.report import Report
    
    query = select(func.count()).select_from(Report).where(
        Report.object_id == object_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

async def count_orders(
    session: AsyncSession,
    object_id: int
) -> int:
    """Посчитать количество заявок по объекту"""
    from model.order import Order
    
    query = select(func.count()).select_from(Order).where(
        Order.object_id == object_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    object_create: ObjectCreate
) -> Object:
    """Создать новый объект"""
    obj = Object(**object_create.dict())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    object_id: int,
    object_update: ObjectUpdate
) -> Optional[Object]:
    """Обновить объект"""
    obj = await get_by_id(session, object_id, load_relations=False)
    if not obj:
        return None
    
    update_data = object_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(obj, field):
            setattr(obj, field, value)
    
    await session.commit()
    await session.refresh(obj)
    return obj

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    object_id: int
) -> bool:
    """Удалить объект"""
    obj = await session.get(Object, object_id)
    if not obj:
        return False
    
    await session.delete(obj)
    await session.commit()
    return True