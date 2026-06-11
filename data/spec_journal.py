from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List, Tuple

from model.spec_journal import Spec_Journal
from schema.spec_journal import SpecJournalCreate, SpecJournalUpdate

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_spec_journal_by_id(
    session: AsyncSession,
    spec_journal_id: int,
) -> Optional[Spec_Journal]:
    """Получить тип журнала по ID"""
    query = select(Spec_Journal).where(Spec_Journal.id == spec_journal_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_journal_by_name(
    session: AsyncSession,
    name: str,
) -> Optional[Spec_Journal]:
    """Получить тип журнала по названию"""
    query = select(Spec_Journal).where(Spec_Journal.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_journal_by_code(
    session: AsyncSession,
    code: str,
) -> Optional[Spec_Journal]:
    """Получить тип журнала по машинному коду"""
    query = select(Spec_Journal).where(Spec_Journal.code == code)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_spec_journal_all(session: AsyncSession) -> List[Spec_Journal]:
    """Получить все типы журналов"""
    query = select(Spec_Journal).order_by(Spec_Journal.name)
    result = await session.execute(query)
    return result.scalars().all()


@timer
async def get_spec_journal_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> Tuple[List[Spec_Journal], int]:
    """Получить список типов журналов с пагинацией"""
    query = select(Spec_Journal)
    count_query = select(func.count()).select_from(Spec_Journal)

    if search:
        search_filter = or_(
            Spec_Journal.name.ilike(f"%{search}%"),
            Spec_Journal.short_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if sort_by and hasattr(Spec_Journal, sort_by):
        column = getattr(Spec_Journal, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Spec_Journal.name)

    query = query.offset(skip).limit(limit)

    result = await session.execute(query)
    items = result.scalars().all()

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    return items, total


# ========== ПОЛУЧЕНИЕ ДЛЯ ВЫПАДАЮЩИХ СПИСКОВ ==========

@timer
async def get_spec_journal_options(session: AsyncSession) -> List[Spec_Journal]:
    """Получить минимальную информацию о типах журналов для выпадающих списков"""
    query = select(Spec_Journal).order_by(Spec_Journal.name)
    result = await session.execute(query)
    return result.scalars().all()


# ========== ПРОВЕРКА УНИКАЛЬНОСТИ ==========

@timer
async def check_spec_journal_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None,
) -> bool:
    """Проверить, существует ли тип журнала с таким названием"""
    query = select(Spec_Journal).where(Spec_Journal.name == name)
    if exclude_id:
        query = query.where(Spec_Journal.id != exclude_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


@timer
async def check_spec_journal_code_exists(
    session: AsyncSession,
    code: str,
    exclude_id: Optional[int] = None,
) -> bool:
    """Проверить, существует ли тип журнала с таким машинным кодом"""
    query = select(Spec_Journal).where(Spec_Journal.code == code)
    if exclude_id:
        query = query.where(Spec_Journal.id != exclude_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


# ========== СОЗДАНИЕ ==========

@timer
async def create_spec_journal(
    session: AsyncSession,
    spec_journal_create: SpecJournalCreate,
) -> Spec_Journal:
    """Создать новый тип журнала"""
    spec_journal = Spec_Journal(**spec_journal_create.model_dump())
    session.add(spec_journal)
    await session.commit()
    await session.refresh(spec_journal)
    return spec_journal


# ========== ОБНОВЛЕНИЕ ==========

@timer
async def update_spec_journal(
    session: AsyncSession,
    spec_journal_id: int,
    spec_journal_update: SpecJournalUpdate,
) -> Optional[Spec_Journal]:
    """Обновить тип журнала"""
    spec_journal = await get_spec_journal_by_id(session, spec_journal_id)
    if not spec_journal:
        return None

    update_data = spec_journal_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(spec_journal, field):
            setattr(spec_journal, field, value)

    await session.commit()
    await session.refresh(spec_journal)
    return spec_journal


# ========== ШАБЛОН ДОКУМЕНТА ==========

@timer
async def set_spec_journal_template(
    session: AsyncSession,
    spec_journal_id: int,
    template_filename: str,
    template_storage_path: str,
) -> Optional[Spec_Journal]:
    """Прописать в spec_journal имя+путь только что загруженного шаблона"""
    spec_journal = await get_spec_journal_by_id(session, spec_journal_id)
    if not spec_journal:
        return None
    spec_journal.template_filename = template_filename
    spec_journal.template_storage_path = template_storage_path
    await session.commit()
    await session.refresh(spec_journal)
    return spec_journal


@timer
async def clear_spec_journal_template(
    session: AsyncSession,
    spec_journal_id: int,
) -> Optional[Spec_Journal]:
    """Снять привязку шаблона (NULL в обе колонки). Файл удаляется вызывающим сервисом."""
    spec_journal = await get_spec_journal_by_id(session, spec_journal_id)
    if not spec_journal:
        return None
    spec_journal.template_filename = None
    spec_journal.template_storage_path = None
    await session.commit()
    await session.refresh(spec_journal)
    return spec_journal


# ========== УДАЛЕНИЕ ==========

@timer
async def delete_spec_journal(
    session: AsyncSession,
    spec_journal_id: int,
) -> bool:
    """Удалить тип журнала"""
    spec_journal = await session.get(Spec_Journal, spec_journal_id)
    if not spec_journal:
        return False
    await session.delete(spec_journal)
    await session.commit()
    return True
