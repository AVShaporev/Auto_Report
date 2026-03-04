from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_contract import Spec_Contract
from schema.spec_contract import SpecContractCreate, SpecContractUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    spec_contract_id: int,
    load_contracts: bool = False
) -> Optional[Spec_Contract]:
    """
    Получить тип договора по ID
    
    Args:
        session: Сессия БД
        spec_contract_id: ID типа договора
        load_contracts: Загружать связанные договоры
    """
    query = select(Spec_Contract).where(Spec_Contract.id == spec_contract_id)
    
    if load_contracts:
        query = query.options(selectinload(Spec_Contract.contracts))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Contract]:
    """
    Получить тип договора по названию
    """
    query = select(Spec_Contract).where(Spec_Contract.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    load_contracts: bool = False
) -> List[Spec_Contract]:
    """
    Получить все типы договоров
    """
    query = select(Spec_Contract).order_by(Spec_Contract.name)
    
    if load_contracts:
        query = query.options(selectinload(Spec_Contract.contracts))
    
    result = await session.execute(query)
    return result.scalars().all()

async def get_paginated(
                        session: AsyncSession,
                        skip: int = 0,
                        limit: int = 20,
                        search: Optional[str] = None,
                        sort_by: str = "name",
                        sort_order: str = "asc",
                        load_contracts: bool = False
                        ) -> Tuple[List[Spec_Contract], int]:
    """
    Получить список типов договоров с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Contract)
    count_query = select(func.count()).select_from(Spec_Contract)
    
    # Поиск
    if search:
        search_filter = or_(
            Spec_Contract.name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Contract, sort_by):
        column = getattr(Spec_Contract, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Contract.name)

    # Загрузка связанных данных (если запрошено)
    if load_contracts:
        query = query.options(selectinload(Spec_Contract.contracts))

    # Пагинация
    query = query.offset(skip).limit(limit)
    
    # Выполнение
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    return items, total

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ ==========

async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """
    Проверить, существует ли тип договора с таким названием
    """
    query = select(Spec_Contract).where(Spec_Contract.name == name)
    if exclude_id:
        query = query.where(Spec_Contract.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    spec_contract_create: SpecContractCreate
) -> Spec_Contract:
    """
    Создать новый тип договора
    """
    spec_contract = Spec_Contract(**spec_contract_create.dict())
    session.add(spec_contract)
    await session.commit()
    await session.refresh(spec_contract)
    return spec_contract

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    spec_contract_id: int,
    spec_contract_update: SpecContractUpdate
) -> Optional[Spec_Contract]:
    """
    Обновить тип договора
    """
    spec_contract = await get_by_id(session, spec_contract_id, load_contracts=False)
    if not spec_contract:
        return None
    
    # Получаем данные для обновления (только переданные поля)
    update_data = spec_contract_update.dict(exclude_unset=True)
    
    # Обновляем поля
    for field, value in update_data.items():
        if hasattr(spec_contract, field):
            setattr(spec_contract, field, value)
    
    await session.commit()
    await session.refresh(spec_contract)
    return spec_contract

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    spec_contract_id: int
) -> bool:
    """
    Удалить тип договора
    """
    spec_contract = await get_by_id(session, spec_contract_id, load_contracts=True)
    if not spec_contract:
        return False
    
    # Проверяем, есть ли связанные договоры
    if spec_contract.contracts and len(spec_contract.contracts) > 0:
        raise ValueError(f"Невозможно удалить тип договора '{spec_contract.name}': есть связанные договоры")
    
    await session.delete(spec_contract)
    await session.commit()
    return True

# ========== ДОПОЛНИТЕЛЬНЫЕ ОПЕРАЦИИ ==========

async def get_with_contracts_count(
    session: AsyncSession,
    spec_contract_id: int
) -> Tuple[Optional[Spec_Contract], int]:
    """
    Получить тип договора и количество связанных договоров
    """
    spec_contract = await get_by_id(session, spec_contract_id, load_contracts=True)
    if not spec_contract:
        return None, 0
    
    contracts_count = len(spec_contract.contracts) if spec_contract.contracts else 0
    return spec_contract, contracts_count