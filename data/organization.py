from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from model.organization import Organization
from schema.organization import OrganizationCreate, OrganizationUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_organization_by_id(
                                session: AsyncSession,
                                org_id: int,
                                load_relations: bool = True
                                ) -> Optional[Organization]:
    """
    Получить организацию по ID
    
    Args:
        session: Сессия БД
        org_id: ID организации
        load_relations: Загружать связанные объекты
    """
    query = select(Organization).where(Organization.id == org_id)
    
    if load_relations:
        query = query.options(
                            selectinload(Organization.bank),
                            selectinload(Organization.region),
                            selectinload(Organization.arial),
                            selectinload(Organization.locality),
                            selectinload(Organization.street),
                            selectinload(Organization.spec_build),
                            selectinload(Organization.spec_room),
                            selectinload(Organization.spec_job_title)
                            )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_organization_by_name(
                                    session: AsyncSession,
                                    name: str
                                    ) -> Optional[Organization]:
    """
    Получить организацию по названию
    """
    query = select(Organization).where(Organization.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_organization_by_inn(
                                        session: AsyncSession,
                                        inn: str
                                    ) -> Optional[Organization]:
    """
    Получить организацию по ИНН
    """
    query = select(Organization).where(Organization.inn == inn)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_organization_all(
                                session: AsyncSession,
                                load_relations: bool = False
                                ) -> List[Organization]:
    """
    Получить все организации
    """
    query = select(Organization).order_by(Organization.name)
    
    if load_relations:
        query = query.options(
                                selectinload(Organization.bank),
                                selectinload(Organization.region)
                                )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_organization_paginated(
                                        session: AsyncSession,
                                        skip: int = 0,
                                        limit: int = 20,
                                        search: Optional[str] = None,
                                        customer: Optional[bool] = None,
                                        executor: Optional[bool] = None,
                                        region_id: Optional[int] = None,
                                        bank_id: Optional[int] = None,
                                        sort_by: str = "name",
                                        sort_order: str = "asc"
                                        ) -> Tuple[List[Organization], int]:
    """
    Получить список организаций с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Organization)
    count_query = select(func.count()).select_from(Organization)
    
    # Поиск по нескольким полям
    if search:
        search_filter = or_(
                            Organization.name.ilike(f"%{search}%"),
                            Organization.short_name.ilike(f"%{search}%"),
                            Organization.inn.ilike(f"%{search}%")
                            )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтры
    if customer is not None:
        query = query.where(Organization.customer == customer)
        count_query = count_query.where(Organization.customer == customer)
    
    if executor is not None:
        query = query.where(Organization.executor == executor)
        count_query = count_query.where(Organization.executor == executor)
    
    if region_id:
        query = query.where(Organization.region_id == region_id)
        count_query = count_query.where(Organization.region_id == region_id)
    
    if bank_id:
        query = query.where(Organization.bank_id == bank_id)
        count_query = count_query.where(Organization.bank_id == bank_id)
    
    query = query.options(
                            selectinload(Organization.bank),
                            selectinload(Organization.region)
                            )


    # Сортировка
    if sort_by and hasattr(Organization, sort_by):
        column = getattr(Organization, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Organization.name)
    
    # Пагинация
    query = query.offset(skip).limit(limit)
    
    # Выполнение
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    return items, total

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_organization_name_exists(
                                        session: AsyncSession,
                                        name: str,
                                        exclude_id: Optional[int] = None
                                        ) -> bool:
    """Проверить, существует ли организация с таким названием"""
    query = select(Organization).where(Organization.name == name)
    if exclude_id:
        query = query.where(Organization.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_organization_short_name_exists(
                                                session: AsyncSession,
                                                short_name: str,
                                                exclude_id: Optional[int] = None
                                                ) -> bool:
    """Проверить, существует ли организация с таким сокращенным названием"""
    query = select(Organization).where(Organization.short_name == short_name)
    if exclude_id:
        query = query.where(Organization.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

@timer
async def check_organization_inn_exists(
                                        session: AsyncSession,
                                        inn: str,
                                        exclude_id: Optional[int] = None
                                        ) -> bool:
    """Проверить, существует ли организация с таким ИНН"""
    query = select(Organization).where(Organization.inn == inn)
    if exclude_id:
        query = query.where(Organization.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== СОЗДАНИЕ ==========

@timer
async def create_organization(
                                session: AsyncSession,
                                org_create: OrganizationCreate
                                ) -> Organization:
    """
    Создать новую организацию
    """
    organization = Organization(**org_create.dict())
    session.add(organization)
    await session.commit()
    await session.refresh(organization)
    return organization

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_organization(
                                session: AsyncSession,
                                org_id: int,
                                org_update: OrganizationUpdate
                                ) -> Optional[Organization]:
    """
    Обновить организацию
    """
    organization = await get_organization_by_id(session, org_id, load_relations=False)
    if not organization:
        return None
    
    # Получаем данные для обновления (только переданные поля)
    update_data = org_update.dict(exclude_unset=True)
    
    # Обновляем поля
    for field, value in update_data.items():
        if hasattr(organization, field):
            setattr(organization, field, value)
    
    await session.commit()
    await session.refresh(organization)
    return organization

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_organization(
                                session: AsyncSession,
                                org_id: int
                                ) -> bool:
    """
    Удалить организацию
    """
    organization = await get_organization_by_id(session, org_id, load_relations=False)
    if not organization:
        return False
    
    await session.delete(organization)
    await session.commit()
    return True