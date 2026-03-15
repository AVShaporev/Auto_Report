from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_job_title import Spec_Job_Title
from schema.spec_job_title import SpecJobTitleCreate, SpecJobTitleUpdate

from utils.timer import timer


# ========== ПОДСЧЕТ СВЯЗАННЫХ ОБЪЕКТОВ ==========

@timer
async def count_organizations(
    session: AsyncSession,
    spec_job_title_id: int
) -> int:
    """
    Посчитать количество организаций с данной должностью руководителя
    
    Это эффективнее, чем загружать все объекты через relationship
    """
    from model.organization import Organization
    
    query = select(func.count()).select_from(Organization).where(
        Organization.spec_job_title_id == spec_job_title_id
    )
    result = await session.execute(query)
    return result.scalar() or 0
    
# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_by_id(
    session: AsyncSession,
    spec_job_title_id: int,
    *,
    load_organizations: bool = False  # Флаг для загрузки связанных организаций
) -> Optional[Spec_Job_Title]:
    """
    Получить должность руководителя по ID
    
    Args:
        session: Сессия БД
        spec_job_title_id: ID должности
        load_organizations: Если True, немедленно загрузить связанные организации
    """
    query = select(Spec_Job_Title).where(Spec_Job_Title.id == spec_job_title_id)
    
    if load_organizations:
        # Загружаем связанные организации в этом же запросе
        query = query.options(selectinload(Spec_Job_Title.organizations))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Spec_Job_Title]:
    """
    Получить должность руководителя по названию
    """
    query = select(Spec_Job_Title).where(Spec_Job_Title.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

@timer
async def get_all(
    session: AsyncSession,
    *,
    load_organizations: bool = False
) -> List[Spec_Job_Title]:
    """
    Получить все должности руководителей
    """
    query = select(Spec_Job_Title).order_by(Spec_Job_Title.name)
    
    if load_organizations:
        query = query.options(selectinload(Spec_Job_Title.organizations))
    
    result = await session.execute(query)
    return result.scalars().all()

@timer
async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    *,
    load_organizations: bool = False
) -> Tuple[List[Spec_Job_Title], int]:
    """
    Получить список должностей руководителей с пагинацией
    """
    # Базовый запрос
    query = select(Spec_Job_Title)
    count_query = select(func.count()).select_from(Spec_Job_Title)
    
    # Поиск
    if search:
        search_filter = or_(
            Spec_Job_Title.name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Сортировка
    if sort_by and hasattr(Spec_Job_Title, sort_by):
        column = getattr(Spec_Job_Title, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Job_Title.name)
    
    # Загрузка связанных данных (если запрошено)
    if load_organizations:
        query = query.options(selectinload(Spec_Job_Title.organizations))
    
    # Пагинация
    query = query.offset(skip).limit(limit)
    
    # Выполнение
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    return items, total

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ ==========

@timer
async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """
    Проверить, существует ли должность с таким названием
    """
    query = select(Spec_Job_Title).where(Spec_Job_Title.name == name)
    if exclude_id:
        query = query.where(Spec_Job_Title.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== СОЗДАНИЕ ==========

@timer
async def create(
    session: AsyncSession,
    spec_job_title_create: SpecJobTitleCreate
) -> Spec_Job_Title:
    """
    Создать новую должность руководителя
    """
    spec_job_title = Spec_Job_Title(**spec_job_title_create.dict())
    session.add(spec_job_title)
    await session.commit()
    await session.refresh(spec_job_title)
    return spec_job_title

# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update(
    session: AsyncSession,
    spec_job_title_id: int,
    spec_job_title_update: SpecJobTitleUpdate
) -> Optional[Spec_Job_Title]:
    """
    Обновить должность руководителя
    """
    spec_job_title = await get_by_id(session, spec_job_title_id, load_organizations=False)
    if not spec_job_title:
        return None
    
    # Получаем данные для обновления (только переданные поля)
    update_data = spec_job_title_update.dict(exclude_unset=True)
    
    # Обновляем поля
    for field, value in update_data.items():
        if hasattr(spec_job_title, field):
            setattr(spec_job_title, field, value)
    
    await session.commit()
    await session.refresh(spec_job_title)
    return spec_job_title

# ========== УДАЛЕНИЕ ==========

@timer
async def delete(
    session: AsyncSession,
    spec_job_title_id: int
) -> bool:
    """
    Удалить должность руководителя
    """
    spec_job_title = await session.get(Spec_Job_Title, spec_job_title_id)
    if not spec_job_title:
        return False
    
    await session.delete(spec_job_title)
    await session.commit()
    return True