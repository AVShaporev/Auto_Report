from typing import Optional, List, Tuple
from fastapi import HTTPException

from model.user import User
from model.operation import Operation
from data import operation as operation_data
from schema.operation import OperationCreate, OperationUpdate
from schema.pagination import PaginationParams
from database.database import new_session


# ========== RBAC ==========

async def check_permission(
    current_user: User,
    permission: str,
    action: str = "выполнения операции",
) -> None:
    if not hasattr(current_user.role, permission):
        raise HTTPException(
            status_code=500,
            detail=f"Право {permission} не определено в системе",
        )
    if not getattr(current_user.role, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Недостаточно прав для {action}",
        )


# ========== ПОЛУЧЕНИЕ ==========

def _pack(op: Operation) -> dict:
    return {
        "id": op.id,
        "name": op.name,
        "short_name": op.short_name,
        "description": op.description,
        "spec_equipments": [
            {"id": se.id, "name": se.name} for se in (op.spec_equipments or [])
        ],
    }


def _pack_list(op: Operation) -> dict:
    return {
        "id": op.id,
        "name": op.name,
        "short_name": op.short_name,
        "spec_equipments_count": len(op.spec_equipments or []),
        "spec_equipments": [
            {"id": se.id, "name": se.name} for se in (op.spec_equipments or [])
        ],
    }


async def get_operation_with_details(
    operation_id: int,
    current_user: User,
) -> dict:
    await check_permission(current_user, "operation_read", "просмотра операции")
    async with new_session() as session:
        op = await operation_data.get_operation_by_id(session, operation_id)
        if not op:
            raise HTTPException(404, detail=f"Операция с id {operation_id} не найдена")
        return _pack(op)


async def get_operations_paginated_with_details(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_equipment_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> Tuple[List[dict], int]:
    await check_permission(current_user, "operation_read", "просмотра списка операций")
    async with new_session() as session:
        items, total = await operation_data.get_operation_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_equipment_id=spec_equipment_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return [_pack_list(op) for op in items], total


async def get_all_operations(
    current_user: User,
) -> List[dict]:
    await check_permission(current_user, "operation_read", "просмотра операций")
    async with new_session() as session:
        items = await operation_data.get_operation_all(session)
        return [_pack_list(op) for op in items]


async def get_operation_options(
    current_user: User,
    spec_equipment_id: Optional[int] = None,
) -> List[dict]:
    await check_permission(current_user, "operation_read", "просмотра операций")
    async with new_session() as session:
        items = await operation_data.get_operation_options(session, spec_equipment_id)
        return [
            {"id": op.id, "name": op.name, "short_name": op.short_name}
            for op in items
        ]


# ========== СОЗДАНИЕ ==========

async def create_operation(
    payload: OperationCreate,
    current_user: User,
) -> dict:
    await check_permission(current_user, "operation_create", "создания операции")
    async with new_session() as session:
        if await operation_data.check_operation_name_exists(session, payload.name):
            raise HTTPException(400, detail=f"Операция с названием '{payload.name}' уже существует")

        spec_equipments = await operation_data.get_spec_equipments_by_ids(
            session, payload.spec_equipment_ids
        )
        # Защита от «битых» id'шников
        if len(spec_equipments) != len(set(payload.spec_equipment_ids)):
            found = {se.id for se in spec_equipments}
            missing = sorted(set(payload.spec_equipment_ids) - found)
            raise HTTPException(
                400, detail=f"Не найдены типы оборудования с id: {missing}"
            )

        op = await operation_data.create_operation(
            session,
            name=payload.name,
            short_name=payload.short_name,
            description=payload.description,
            spec_equipments=spec_equipments,
        )
        return _pack(op)


# ========== ОБНОВЛЕНИЕ ==========

async def update_operation(
    operation_id: int,
    payload: OperationUpdate,
    current_user: User,
) -> dict:
    await check_permission(current_user, "operation_modify", "изменения операции")
    async with new_session() as session:
        existing = await operation_data.get_operation_by_id(session, operation_id)
        if not existing:
            raise HTTPException(404, detail=f"Операция с id {operation_id} не найдена")

        if payload.name and payload.name != existing.name:
            if await operation_data.check_operation_name_exists(
                session, payload.name, exclude_id=operation_id
            ):
                raise HTTPException(
                    400, detail=f"Операция с названием '{payload.name}' уже существует"
                )

        spec_equipments = None
        if payload.spec_equipment_ids is not None:
            spec_equipments = await operation_data.get_spec_equipments_by_ids(
                session, payload.spec_equipment_ids
            )
            if len(spec_equipments) != len(set(payload.spec_equipment_ids)):
                found = {se.id for se in spec_equipments}
                missing = sorted(set(payload.spec_equipment_ids) - found)
                raise HTTPException(
                    400, detail=f"Не найдены типы оборудования с id: {missing}"
                )

        op = await operation_data.update_operation(
            session,
            operation_id,
            name=payload.name,
            short_name=payload.short_name,
            description=payload.description,
            spec_equipments=spec_equipments,
        )
        return _pack(op)


# ========== УДАЛЕНИЕ ==========

async def delete_operation(
    operation_id: int,
    current_user: User,
) -> bool:
    await check_permission(current_user, "operation_delete", "удаления операции")
    async with new_session() as session:
        existing = await operation_data.get_operation_by_id(session, operation_id)
        if not existing:
            raise HTTPException(404, detail=f"Операция с id {operation_id} не найдена")
        return await operation_data.delete_operation(session, operation_id)
