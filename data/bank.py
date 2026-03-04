from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.bank import Bank
from schema.bank import BankCreate, BankUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    bank_id: int,
    *,
    load_organizations: bool = False
) -> Optional[Bank]:
    """
    Получить банк по ID
    
    Args:
        session: Сессия БД
        bank_id: ID банка
        load_organizations: Если True, загрузить связанные организации
    """
    query = select(Bank).where(Bank.id == bank_id)
    
    if load_organizations:
        query = query.options(selectinload(Bank.organizations))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Bank]:
    """Получить банк по названию"""
    query = select(Bank).where(Bank.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_bik(
    session: AsyncSession,
    bik: str
) -> Optional[Bank]:
    """Получить банк по БИК"""
    query = select(Bank).where(Bank.bik == bik)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_inn(
    session: AsyncSession,
    inn: str
) -> Optional[Bank]:
    """Получить банк по ИНН"""
    query = select(Bank).where(Bank.inn == inn)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    *,
    load_organizations: bool = False
) -> List[Bank]:
    """Получить все банки"""
    query = select(Bank).order_by(Bank.name)
    
    if load_organizations:
        query = query.options(selectinload(Bank.organizations))
    
    result = await session.execute(query)
    return result.scalars().all()

async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_organizations: bool = False
) -> Tuple[List[Bank], int]:
    """
    Получить список банков с пагинацией и поиском
    """
    # Базовый запрос
    query = select(Bank)
    count_query = select(func.count()).select_from(Bank)
    
    # Поиск по названию, БИК или ИНН
    if search:
        search_filter = or_(
            Bank.name.ilike(f"%{search}%"),
            Bank.bik.ilike(f"%{search}%"),
            Bank.inn.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Bank, sort_by):
        column = getattr(Bank, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Bank.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_organizations:
        query = query.options(selectinload(Bank.organizations))
    
    # Пагинация
    query = query.offset(skip).limit(limit)
    
    # Выполнение
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    return items, total

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли банк с таким названием"""
    query = select(Bank).where(Bank.name == name)
    if exclude_id:
        query = query.where(Bank.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_bik_exists(
    session: AsyncSession,
    bik: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли банк с таким БИК"""
    query = select(Bank).where(Bank.bik == bik)
    if exclude_id:
        query = query.where(Bank.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

async def check_inn_exists(
    session: AsyncSession,
    inn: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли банк с таким ИНН"""
    query = select(Bank).where(Bank.inn == inn)
    if exclude_id:
        query = query.where(Bank.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

async def count_organizations(
    session: AsyncSession,
    bank_id: int
) -> int:
    """
    Посчитать количество организаций, использующих данный банк
    
    Это эффективнее, чем загружать все объекты через relationship
    """
    from model.organization import Organization
    
    query = select(func.count()).select_from(Organization).where(
        Organization.bank_id == bank_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    bank_create: BankCreate
) -> Bank:
    """Создать новый банк"""
    bank = Bank(**bank_create.dict())
    session.add(bank)
    await session.commit()
    await session.refresh(bank)
    return bank

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    bank_id: int,
    bank_update: BankUpdate
) -> Optional[Bank]:
    """Обновить банк"""
    bank = await get_by_id(session, bank_id, load_organizations=False)
    if not bank:
        return None
    
    update_data = bank_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(bank, field):
            setattr(bank, field, value)
    
    await session.commit()
    await session.refresh(bank)
    return bank

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    bank_id: int
) -> bool:
    """Удалить банк"""
    bank = await session.get(Bank, bank_id)
    if not bank:
        return False
    
    await session.delete(bank)
    await session.commit()
    return True