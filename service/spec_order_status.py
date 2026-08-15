from typing import List, Optional, Tuple

from fastapi import HTTPException

from model.user import User
from model.spec_order_status import Spec_Order_Status
from data import spec_order_status as spec_order_status_data
from schema.spec_order_status import SpecOrderStatusCreate, SpecOrderStatusUpdate
from schema.pagination import PaginationParams
from database.database import new_session


# ========== ВСПОМОГАТЕЛЬНЫЕ ==========

async def check_permission(
    current_user: User, permission: str, action: str = "выполнения операции"
) -> None:
    if not hasattr(current_user.role, permission):
        raise HTTPException(status_code=500, detail=f"Право {permission} не определено")
    if not getattr(current_user.role, permission):
        raise HTTPException(status_code=403, detail=f"Недостаточно прав для {action}")


def _to_response(row: Spec_Order_Status, orders_count: int = 0) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "is_default": row.is_default,
        "orders_count": orders_count,
    }


# ========== ПОЛУЧЕНИЕ ==========

async def get_spec_order_status_options(current_user: User) -> List[Spec_Order_Status]:
    """Публичный options — нужен всем аутентифицированным юзерам для селектов
    (даже без права spec_order_status_read). Иначе даже создать заявку нельзя."""
    async with new_session() as session:
        return await spec_order_status_data.get_spec_order_status_all(session)


async def get_spec_order_status_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> Tuple[List[dict], int]:
    await check_permission(current_user, "spec_order_status_read", "просмотра справочника статусов заявок")

    async with new_session() as session:
        items, total = await spec_order_status_data.get_spec_order_status_paginated(
            session, skip=pagination.skip, limit=pagination.limit,
            search=search, sort_by=sort_by, sort_order=sort_order,
        )
        result = []
        for item in items:
            orders_count = await spec_order_status_data.count_orders_by_status(session, item.id)
            result.append(_to_response(item, orders_count))
        return result, total


async def get_spec_order_status_with_stats(
    spec_order_status_id: int, current_user: User
) -> dict:
    await check_permission(current_user, "spec_order_status_read", "просмотра справочника статусов заявок")

    async with new_session() as session:
        row = await spec_order_status_data.get_spec_order_status_by_id(session, spec_order_status_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Статус с id {spec_order_status_id} не найден")
        orders_count = await spec_order_status_data.count_orders_by_status(session, spec_order_status_id)
        return _to_response(row, orders_count)


# ========== СОЗДАНИЕ ==========

async def create_spec_order_status(
    payload: SpecOrderStatusCreate, current_user: User
) -> dict:
    await check_permission(current_user, "spec_order_status_create", "создания статусов заявок")

    async with new_session() as session:
        if await spec_order_status_data.check_name_exists(session, payload.name):
            raise HTTPException(status_code=400, detail=f"Статус с именем '{payload.name}' уже существует")

        row = await spec_order_status_data.create_spec_order_status(session, payload)
        return _to_response(row, orders_count=0)


# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_order_status(
    spec_order_status_id: int, payload: SpecOrderStatusUpdate, current_user: User
) -> dict:
    await check_permission(current_user, "spec_order_status_modify", "изменения статусов заявок")

    async with new_session() as session:
        existing = await spec_order_status_data.get_spec_order_status_by_id(session, spec_order_status_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Статус с id {spec_order_status_id} не найден")

        if payload.name and payload.name != existing.name:
            if await spec_order_status_data.check_name_exists(session, payload.name, exclude_id=spec_order_status_id):
                raise HTTPException(status_code=400, detail=f"Статус с именем '{payload.name}' уже существует")

        # Запрещаем убрать is_default с текущего дефолтного (без переноса на другой)
        # — партиал-уник разрешит, но система останется без дефолтной строки,
        # autogen начнёт брать MIN(id). Явно ругаемся.
        if payload.is_default is False and existing.is_default:
            raise HTTPException(
                status_code=400,
                detail="Нельзя снять флаг 'по умолчанию' — сначала назначьте другой статус дефолтным.",
            )

        row = await spec_order_status_data.update_spec_order_status(
            session, spec_order_status_id, payload
        )
        orders_count = await spec_order_status_data.count_orders_by_status(session, spec_order_status_id)
        return _to_response(row, orders_count)


# ========== УДАЛЕНИЕ ==========

async def delete_spec_order_status(
    spec_order_status_id: int, current_user: User
) -> bool:
    await check_permission(current_user, "spec_order_status_delete", "удаления статусов заявок")

    async with new_session() as session:
        row = await spec_order_status_data.get_spec_order_status_by_id(session, spec_order_status_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Статус с id {spec_order_status_id} не найден")

        if row.is_default:
            raise HTTPException(
                status_code=400,
                detail="Нельзя удалить статус, помеченный 'по умолчанию' — сначала назначьте другой дефолтным.",
            )

        orders_count = await spec_order_status_data.count_orders_by_status(session, spec_order_status_id)
        if orders_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Нельзя удалить статус '{row.name}': используется в {orders_count} заявках.",
            )

        return await spec_order_status_data.delete_spec_order_status(session, spec_order_status_id)
