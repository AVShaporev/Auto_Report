from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_build import Spec_Build
from schema.spec_build import SpecBuildCreate, SpecBuildUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    spec_build_id: int,
    *,
    load_relations: bool = False
) -> Optional[Spec_Build]:
    """
    Получить тип строения по ID
    
    Args:
        session: Сессия БД
        spec_build_id: ID типа строения
        load_relations: Если True, загрузить связанные данные (organizations, objects)
    """
    query = select(Spec_Build).where(Spec_Build.id == spec_build_id)
    
    if load_relations:
        query = query.options(
            selectinload(Spec_Build.organizations),
            selectinload(Spec_Build.objects)
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Build]:
    """Получить тип строения по названию"""
    query = select(Spec_Build).where(Spec_Build.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    *,
    load_relations: bool = False
) -> List[Spec_Build]:
    """Получить все типы строений"""
    query = select(Spec_Build).order_by(Spec_Build.name)
    
    if load_relations:
        query = query.options(
            selectinload(Spec_Build.organizations),
            selectinload(Spec_Build.objects)
        )
    
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
    load_relations: bool = False
) -> Tuple[List[Spec_Build], int]:
    """
    Получить список типов строений с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Build)
    count_query = select(func.count()).select_from(Spec_Build)
    
    # Поиск по названию
    if search:
        search_filter = Spec_Build.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Build, sort_by):
        column = getattr(Spec_Build, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Build.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
            selectinload(Spec_Build.organizations),
            selectinload(Spec_Build.objects)
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
) -> List[Spec_Build]:
    """
    Получить минимальную информацию о типах строений для выпадающих списков
    """
    query = select(Spec_Build).order_by(Spec_Build.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Проверить, существует ли тип строения с таким названием"""
    query = select(Spec_Build).where(Spec_Build.name == name)
    if exclude_id:
        query = query.where(Spec_Build.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

async def count_organizations(
    session: AsyncSession,
    spec_build_id: int
) -> int:
    """
    Посчитать количество организаций с данным типом строения
    """
    from model.organization import Organization
    
    query = select(func.count()).select_from(Organization).where(
        Organization.spec_build_id == spec_build_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

async def count_objects(
    session: AsyncSession,
    spec_build_id: int
) -> int:
    """
    Посчитать количество объектов с данным типом строения
    """
    from model.object import Object
    
    query = select(func.count()).select_from(Object).where(
        Object.spec_build_id == spec_build_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    spec_build_create: SpecBuildCreate
) -> Spec_Build:
    """Создать новый тип строения"""
    spec_build = Spec_Build(**spec_build_create.dict())
    session.add(spec_build)
    await session.commit()
    await session.refresh(spec_build)
    return spec_build

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    spec_build_id: int,
    spec_build_update: SpecBuildUpdate
) -> Optional[Spec_Build]:
    """Обновить тип строения"""
    spec_build = await get_by_id(session, spec_build_id, load_relations=False)
    if not spec_build:
        return None
    
    update_data = spec_build_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_build, field):
            setattr(spec_build, field, value)
    
    await session.commit()
    await session.refresh(spec_build)
    return spec_build

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    spec_build_id: int
) -> bool:
    """Удалить тип строения"""
    spec_build = await session.get(Spec_Build, spec_build_id)
    if not spec_build:
        return False
    
    await session.delete(spec_build)
    await session.commit()
    return True