from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.locality import Locality
from schema.locality import LocalityCreate, LocalityUpdate

from utils.timer import timer



# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_locality_by_id(
                            session: AsyncSession,
                            locality_id: int,
                            *,
                            load_relations: bool = False
                            ) -> Optional[Locality]:
    """
    Получить населенный пункт по ID
    
    Args:
        session: Сессия БД
        locality_id: ID населенного пункта
        load_relations: Если True, загрузить связанные данные (spec_locality, organizations, objects)
    """
    query = select(Locality).where(Locality.id == locality_id)
    
    if load_relations:
        query = query.options(
                                selectinload(Locality.spec_locality),
                                selectinload(Locality.organizations),
                                selectinload(Locality.objects)
                                )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_locality_by_name(
                                session: AsyncSession,
                                name: str
                                ) -> Optional[Locality]:
    """Получить населенный пункт по названию"""
    query = select(Locality).where(Locality.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_locality_all(
                            session: AsyncSession,
                            *,
                            load_relations: bool = False
                            ) -> List[Locality]:
    """Получить все населенные пункты"""
    query = select(Locality).order_by(Locality.name)
    
    if load_relations:
        query = query.options(
                                selectinload(Locality.spec_locality),
                                selectinload(Locality.organizations),
                                selectinload(Locality.objects)
                                )
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_locality_paginated(
                                session: AsyncSession,
                                skip: int = 0,
                                limit: int = 20,
                                search: Optional[str] = None,
                                spec_locality_id: Optional[int] = None,
                                sort_by: str = "name",
                                sort_order: str = "asc",
                                *,
                                load_relations: bool = False
                                ) -> Tuple[List[Locality], int]:
    """
    Получить список населенных пунктов с пагинацией и фильтрацией
    """
    # Базовый запрос
    query = select(Locality)
    count_query = select(func.count()).select_from(Locality)
    
    # Поиск по названию
    if search:
        search_filter = Locality.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтр по типу населенного пункта
    if spec_locality_id:
        query = query.where(Locality.spec_locality_id == spec_locality_id)
        count_query = count_query.where(Locality.spec_locality_id == spec_locality_id)
    
    # Сортировка
    if sort_by and hasattr(Locality, sort_by):
        column = getattr(Locality, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Locality.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_relations:
        query = query.options(
                                selectinload(Locality.spec_locality),
                                selectinload(Locality.organizations),
                                selectinload(Locality.objects)
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
async def get_locality_options(
                                session: AsyncSession
                                ) -> List[Locality]:
    """
    Получить минимальную информацию о населенных пунктах для выпадающих списков
    """
    query = select(Locality).order_by(Locality.name)
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_locality_options_by_spec_locality(
                                        session: AsyncSession,
                                        spec_locality_id: int
                                        ) -> List[Locality]:
    """
    Получить минимальную информацию о населенных пунктах для выпадающих списков по типу
    """
    query = select(Locality).where(Locality.spec_locality_id == spec_locality_id).order_by(Locality.name)
    result = await session.execute(query)
    return result.scalars().all()

# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_locality_name_exists(
                                    session: AsyncSession,
                                    name: str,
                                    exclude_id: Optional[int] = None
                                    ) -> bool:
    """Проверить, существует ли населенный пункт с таким названием"""
    query = select(Locality).where(Locality.name == name)
    if exclude_id:
        query = query.where(Locality.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ ТИПА НАСЕЛЕННОГО ПУНКТА ==========

@timer
async def check_locality_spec_locality_exists(
                                                session: AsyncSession,
                                                spec_locality_id: int
                                                ) -> bool:
    """Проверить, существует ли тип населенного пункта с указанным ID"""
    from model.spec_locality import Spec_Locality
    
    query = select(Spec_Locality).where(Spec_Locality.id == spec_locality_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_locality_organizations(
                                        session: AsyncSession,
                                        locality_id: int
                                        ) -> int:
    """
    Посчитать количество организаций в населенном пункте
    """
    from model.organization import Organization
    
    query = select(func.count()).select_from(Organization).where(
        Organization.locality_id == locality_id
    )
    result = await session.execute(query)
    return result.scalar() or 0

@timer
async def count_locality_objects(
                        session: AsyncSession,
                        locality_id: int
                        ) -> int:
    """
    Посчитать количество объектов в населенном пункте
    """
    from model.object import Object
    
    query = select(func.count()).select_from(Object).where(
                                                            Object.locality_id == locality_id
                                                            )
    result = await session.execute(query)
    return result.scalar() or 0

# ========== СОЗДАНИЕ ==========

@timer
async def create_locality(
                            session: AsyncSession,
                            locality_create: LocalityCreate
                            ) -> Locality:
    """Создать новый населенный пункт"""
    locality = Locality(**locality_create.dict())
    session.add(locality)
    await session.commit()
    await session.refresh(locality)
    return locality

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_locality(
                            session: AsyncSession,
                            locality_id: int,
                            locality_update: LocalityUpdate
                            ) -> Optional[Locality]:
    """Обновить населенный пункт"""
    locality = await get_locality_by_id(session, locality_id, load_relations=False)
    if not locality:
        return None
    
    update_data = locality_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(locality, field):
            setattr(locality, field, value)
    
    await session.commit()
    await session.refresh(locality)
    return locality

# ========== УДАЛЕНИЕ ==========

@timer
async def delete_locality(
                            session: AsyncSession,
                            locality_id: int
                            ) -> bool:
    """Удалить населенный пункт"""
    locality = await session.get(Locality, locality_id)
    if not locality:
        return False
    
    await session.delete(locality)
    await session.commit()
    return True