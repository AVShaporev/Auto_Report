from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.operation import Operation
from model.spec_equipment import Spec_Equipment

from utils.timer import timer


# ========== ПОЛУЧЕНИЕ ==========

@timer
async def get_operation_by_id(
    session: AsyncSession,
    operation_id: int,
) -> Optional[Operation]:
    query = (
        select(Operation)
        .options(selectinload(Operation.spec_equipments))
        .where(Operation.id == operation_id)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_operation_by_name(
    session: AsyncSession,
    name: str,
) -> Optional[Operation]:
    query = select(Operation).where(Operation.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@timer
async def get_operation_all(
    session: AsyncSession,
) -> List[Operation]:
    query = (
        select(Operation)
        .options(selectinload(Operation.spec_equipments))
        .order_by(Operation.name)
    )
    result = await session.execute(query)
    return result.scalars().all()


@timer
async def get_operation_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    spec_equipment_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> Tuple[List[Operation], int]:
    query = select(Operation).options(selectinload(Operation.spec_equipments))
    count_query = select(func.count(func.distinct(Operation.id))).select_from(Operation)

    if search:
        search_filter = or_(
            Operation.name.ilike(f"%{search}%"),
            Operation.short_name.ilike(f"%{search}%"),
            Operation.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if spec_equipment_id:
        # Фильтр по конкретному типу оборудования через M2M
        query = query.join(
            Operation.spec_equipments
        ).where(Spec_Equipment.id == spec_equipment_id)
        count_query = (
            select(func.count(func.distinct(Operation.id)))
            .select_from(Operation)
            .join(Operation.spec_equipments)
            .where(Spec_Equipment.id == spec_equipment_id)
        )
        if search:
            count_query = count_query.where(search_filter)

    if sort_by and hasattr(Operation, sort_by):
        col = getattr(Operation, sort_by)
        query = query.order_by(col.desc() if sort_order == "desc" else col.asc())
    else:
        query = query.order_by(Operation.name)

    query = query.offset(skip).limit(limit)

    items = (await session.execute(query)).scalars().unique().all()
    total = (await session.execute(count_query)).scalar() or 0

    return items, total


@timer
async def get_operation_options(
    session: AsyncSession,
    spec_equipment_id: Optional[int] = None,
) -> List[Operation]:
    query = select(Operation).order_by(Operation.name)
    if spec_equipment_id:
        query = (
            query.join(Operation.spec_equipments)
            .where(Spec_Equipment.id == spec_equipment_id)
        )
    result = await session.execute(query)
    return result.scalars().unique().all()


# ========== ПРОВЕРКИ ==========

@timer
async def check_operation_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None,
) -> bool:
    query = select(Operation.id).where(Operation.name == name)
    if exclude_id:
        query = query.where(Operation.id != exclude_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


@timer
async def get_spec_equipments_by_ids(
    session: AsyncSession,
    ids: List[int],
) -> List[Spec_Equipment]:
    if not ids:
        return []
    result = await session.execute(
        select(Spec_Equipment).where(Spec_Equipment.id.in_(ids))
    )
    return result.scalars().all()


# ========== CRUD ==========

@timer
async def create_operation(
    session: AsyncSession,
    name: str,
    short_name: Optional[str],
    description: Optional[str],
    spec_equipments: List[Spec_Equipment],
) -> Operation:
    operation = Operation(
        name=name,
        short_name=short_name,
        description=description,
    )
    operation.spec_equipments = spec_equipments
    session.add(operation)
    await session.commit()
    await session.refresh(operation, attribute_names=["spec_equipments"])
    return operation


@timer
async def update_operation(
    session: AsyncSession,
    operation_id: int,
    *,
    name: Optional[str] = None,
    short_name: Optional[str] = None,
    description: Optional[str] = None,
    spec_equipments: Optional[List[Spec_Equipment]] = None,
) -> Optional[Operation]:
    operation = await get_operation_by_id(session, operation_id)
    if not operation:
        return None

    if name is not None:
        operation.name = name
    if short_name is not None:
        operation.short_name = short_name
    if description is not None:
        operation.description = description
    if spec_equipments is not None:
        operation.spec_equipments = spec_equipments

    await session.commit()
    await session.refresh(operation, attribute_names=["spec_equipments"])
    return operation


@timer
async def delete_operation(
    session: AsyncSession,
    operation_id: int,
) -> bool:
    operation = await session.get(Operation, operation_id)
    if not operation:
        return False
    await session.delete(operation)
    await session.commit()
    return True
