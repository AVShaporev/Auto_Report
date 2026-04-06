from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import date

from model.contract import Contract
from schema.contract import ContractCreate, ContractUpdate

from utils.timer import timer



# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_contract_by_id(
    session: AsyncSession,
    contract_id: int,
    *,
    load_relations: bool = False
) -> Optional[Contract]:
    """
    Получить контракт по ID
    
    Args:
        session: Сессия БД
        contract_id: ID контракта
        load_relations: Если True, загрузить связанные данные
    """
    query = select(Contract).where(Contract.id == contract_id)
    
    if load_relations:
        query = query.options(
            selectinload(Contract.spec_contract),
            selectinload(Contract.customer),
            selectinload(Contract.executor),
            selectinload(Contract.sub_contract_subjects),
            selectinload(Contract.objects),
            selectinload(Contract.reports),
            selectinload(Contract.orders)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_number(
    session: AsyncSession,
    number: str
) -> Optional[Contract]:
    """Получить контракт по номеру"""
    query = select(Contract).where(Contract.number == number)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_contract_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Contract]:
    """Получить все контракты"""
    query = select(Contract).order_by(Contract.number)
    
    if load_relations:
        query = query.options(
            selectinload(Contract.spec_contract),
            selectinload(Contract.customer),
            selectinload(Contract.executor)
        )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_contract_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    spec_contract_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    executor_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    type_contract: Optional[str] = None,
    sort_by: str = "number",
    sort_order: str = "asc",
    *,
    load_relations: bool = False
) -> Tuple[List[Contract], int]:
    """
    Получить список контрактов с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Contract)
    count_query = select(func.count()).select_from(Contract)
    
    # Поиск по номеру и предмету
    if search:
        search_filter = or_(
            Contract.number.ilike(f"%{search}%"),
            Contract.subject.ilike(f"%{search}%"),
            Contract.short_subject.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтры
    if spec_contract_id:
        query = query.where(Contract.spec_contract_id == spec_contract_id)
        count_query = count_query.where(Contract.spec_contract_id == spec_contract_id)
    
    if customer_id:
        query = query.where(Contract.customer_id == customer_id)
        count_query = count_query.where(Contract.customer_id == customer_id)
    
    if executor_id:
        query = query.where(Contract.executor_id == executor_id)
        count_query = count_query.where(Contract.executor_id == executor_id)
    
    if type_contract:
        query = query.where(Contract.type_contract == type_contract)
        count_query = count_query.where(Contract.type_contract == type_contract)
    
    if date_from:
        query = query.where(Contract.date_of_consclusion >= date_from)
        count_query = count_query.where(Contract.date_of_consclusion >= date_from)
    
    if date_to:
        query = query.where(Contract.date_of_completion <= date_to)
        count_query = count_query.where(Contract.date_of_completion <= date_to)
    
    # Сортировка
    if sort_by and hasattr(Contract, sort_by):
        column = getattr(Contract, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Contract.number)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Contract.spec_contract),
            selectinload(Contract.customer),
            selectinload(Contract.executor)
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
async def get_contract_options(
    session: AsyncSession
) -> List[Contract]:
    """
    Получить минимальную информацию о контрактах для выпадающих списков
    """
    query = select(Contract).order_by(Contract.number)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_number_contract_exists(
    session: AsyncSession,
    number: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли контракт с таким номером"""
    query = select(Contract).where(Contract.number == number)
    if exclude_id:
        query = query.where(Contract.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def check_contract_spec_contract_exists(
    session: AsyncSession,
    spec_contract_id: int
) -> bool:
    """Проверить, существует ли тип контракта"""
    from model.spec_contract import Spec_Contract
    
    query = select(Spec_Contract).where(Spec_Contract.id == spec_contract_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_contract_organization_exists(
    session: AsyncSession,
    org_id: int
) -> bool:
    """Проверить, существует ли организация"""
    from model.organization import Organization
    
    query = select(Organization).where(Organization.id == org_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_contract_sub_contracts(
    session: AsyncSession,
    contract_id: int
) -> int:
    """Посчитать количество дополнительных соглашений"""
    from model.sub_contract import Sub_Contract
    
    query = select(func.count()).select_from(Sub_Contract).where(
        Sub_Contract.contract_id == contract_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

@timer
async def count_contract_objects(
    session: AsyncSession,
    contract_id: int
) -> int:
    """Посчитать количество объектов"""
    from model.object import Object
    
    query = select(func.count()).select_from(Object).where(
        Object.contract_id == contract_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

@timer
async def count_contract_reports(
    session: AsyncSession,
    contract_id: int
) -> int:
    """Посчитать количество отчетов"""
    from model.report import Report
    
    query = select(func.count()).select_from(Report).where(
        Report.contract_id == contract_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

@timer
async def count_contract_orders(
    session: AsyncSession,
    contract_id: int
) -> int:
    """Посчитать количество заявок"""
    from model.order import Order
    
    query = select(func.count()).select_from(Order).where(
        Order.contract_id == contract_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

@timer
async def create_contract(
    session: AsyncSession,
    contract_create: ContractCreate
) -> Contract:
    """Создать новый контракт"""
    contract = Contract(**contract_create.dict())
    session.add(contract)
    await session.commit()
    await session.refresh(contract)
    return contract

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_contract(
    session: AsyncSession,
    contract_id: int,
    contract_update: ContractUpdate
) -> Optional[Contract]:
    """Обновить контракт"""
    contract = await get_by_id(session, contract_id, load_relations=False)
    if not contract:
        return None
    
    update_data = contract_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(contract, field):
            setattr(contract, field, value)
    
    await session.commit()
    await session.refresh(contract)
    return contract

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_contract(
    session: AsyncSession,
    contract_id: int
) -> bool:
    """Удалить контракт"""
    contract = await session.get(Contract, contract_id)
    if not contract:
        return False
    
    await session.delete(contract)
    await session.commit()
    return True