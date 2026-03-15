from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import date

from model.sub_contract import Sub_Contract
from schema.sub_contract import SubContractCreate, SubContractUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_by_id(
    session: AsyncSession,
    sub_contract_id: int,
    *,
    load_relations: bool = False
) -> Optional[Sub_Contract]:
    """
    Получить дополнительное соглашение по ID
    
    Args:
        session: Сессия БД
        sub_contract_id: ID дополнительного соглашения
        load_relations: Если True, загрузить связанный контракт
    """
    query = select(Sub_Contract).where(Sub_Contract.id == sub_contract_id)
    
    if load_relations:
        query = query.options(selectinload(Sub_Contract.contract_subject))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_number(
    session: AsyncSession,
    number: str
) -> Optional[Sub_Contract]:
    """Получить дополнительное соглашение по номеру"""
    query = select(Sub_Contract).where(Sub_Contract.number == number)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_contract(
    session: AsyncSession,
    contract_id: int
) -> List[Sub_Contract]:
    """Получить все дополнительные соглашения по контракту"""
    query = select(Sub_Contract).where(Sub_Contract.contract_id == contract_id).order_by(Sub_Contract.date_of_consclusion)
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Sub_Contract]:
    """Получить все дополнительные соглашения"""
    query = select(Sub_Contract).order_by(Sub_Contract.date_of_consclusion.desc())
    
    if load_relations:
        query = query.options(selectinload(Sub_Contract.contract_subject))
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    contract_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "date_of_consclusion",
    sort_order: str = "desc",
    *,
    load_relations: bool = False
) -> Tuple[List[Sub_Contract], int]:
    """
    Получить список дополнительных соглашений с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Sub_Contract)
    count_query = select(func.count()).select_from(Sub_Contract)
    
    # Поиск по номеру и предмету
    if search:
        search_filter = or_(
            Sub_Contract.number.ilike(f"%{search}%"),
            Sub_Contract.subject.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтр по контракту
    if contract_id:
        query = query.where(Sub_Contract.contract_id == contract_id)
        count_query = count_query.where(Sub_Contract.contract_id == contract_id)
    
    # Фильтр по дате
    if date_from:
        query = query.where(Sub_Contract.date_of_consclusion >= date_from)
        count_query = count_query.where(Sub_Contract.date_of_consclusion >= date_from)
    
    if date_to:
        query = query.where(Sub_Contract.date_of_consclusion <= date_to)
        count_query = count_query.where(Sub_Contract.date_of_consclusion <= date_to)
    
    # Сортировка
    if sort_by and hasattr(Sub_Contract, sort_by):
        column = getattr(Sub_Contract, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Sub_Contract.date_of_consclusion.desc())
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(selectinload(Sub_Contract.contract_subject))
    
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
    contract_id: Optional[int] = None
) -> List[Sub_Contract]:
    """
    Получить минимальную информацию о дополнительных соглашениях для выпадающих списков
    """
    query = select(Sub_Contract).order_by(Sub_Contract.date_of_consclusion.desc())
    
    if contract_id:
        query = query.where(Sub_Contract.contract_id == contract_id)
    
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_number_exists(
    session: AsyncSession,
    number: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли дополнительное соглашение с таким номером"""
    query = select(Sub_Contract).where(Sub_Contract.number == number)
    if exclude_id:
        query = query.where(Sub_Contract.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ КОНТРАКТА ==========

@timer
async def check_contract_exists(
    session: AsyncSession,
    contract_id: int
) -> bool:
    """Проверить, существует ли контракт с указанным ID"""
    from model.contract import Contract
    
    query = select(Contract).where(Contract.id == contract_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== СОЗДАНИЕ ==========

@timer
async def create(
    session: AsyncSession,
    sub_contract_create: SubContractCreate
) -> Sub_Contract:
    """Создать новое дополнительное соглашение"""
    sub_contract = Sub_Contract(**sub_contract_create.dict())
    session.add(sub_contract)
    await session.commit()
    await session.refresh(sub_contract)
    return sub_contract

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update(
    session: AsyncSession,
    sub_contract_id: int,
    sub_contract_update: SubContractUpdate
) -> Optional[Sub_Contract]:
    """Обновить дополнительное соглашение"""
    sub_contract = await get_by_id(session, sub_contract_id, load_relations=False)
    if not sub_contract:
        return None
    
    update_data = sub_contract_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(sub_contract, field):
            setattr(sub_contract, field, value)
    
    await session.commit()
    await session.refresh(sub_contract)
    return sub_contract

# ========== УДАЛЕНИЕ ==========

@timer
async def delete(
    session: AsyncSession,
    sub_contract_id: int
) -> bool:
    """Удалить дополнительное соглашение"""
    sub_contract = await session.get(Sub_Contract, sub_contract_id)
    if not sub_contract:
        return False
    
    await session.delete(sub_contract)
    await session.commit()
    return True