from typing import Optional, List, Tuple
from fastapi import HTTPException

from model.user import User
from model.spec_system import Spec_System
from data import spec_system as spec_system_data
from schema.spec_system import SpecSystemCreate, SpecSystemUpdate
from schema.pagination import PaginationParams
from database.database import new_session


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

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

    has_permission = getattr(current_user.role, permission)
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=f"Недостаточно прав для {action}",
        )


# ========== ПОЛУЧЕНИЕ ==========

async def get_spec_system_by_id(spec_system_id: int, current_user: User) -> Spec_System:
    await check_permission(current_user, "spec_system_read", "просмотра типов обслуживаемых систем")
    async with new_session() as session:
        spec_system = await spec_system_data.get_spec_system_by_id(session, spec_system_id)
        if not spec_system:
            raise HTTPException(
                status_code=404,
                detail=f"Тип обслуживаемой системы с id {spec_system_id} не найден",
            )
        return spec_system


async def get_spec_system_with_stats(spec_system_id: int, current_user: User) -> dict:
    await check_permission(current_user, "spec_system_read", "просмотра типов обслуживаемых систем")
    async with new_session() as session:
        spec_system = await spec_system_data.get_spec_system_by_id(session, spec_system_id)
        if not spec_system:
            raise HTTPException(
                status_code=404,
                detail=f"Тип обслуживаемой системы с id {spec_system_id} не найден",
            )
        count = await spec_system_data.count_objects_equipments_by_spec_system(session, spec_system_id)
        return {
            "id": spec_system.id,
            "name": spec_system.name,
            "short_name": spec_system.short_name,
            "is_fire_protection": spec_system.is_fire_protection,
            "objects_equipments_count": count,
        }


async def get_spec_systems_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    is_fire_protection: Optional[bool] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> Tuple[List[dict], int]:
    await check_permission(current_user, "spec_system_read", "просмотра списка типов обслуживаемых систем")
    async with new_session() as session:
        items, total = await spec_system_data.get_spec_system_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            is_fire_protection=is_fire_protection,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        result = []
        for item in items:
            count = await spec_system_data.count_objects_equipments_by_spec_system(session, item.id)
            result.append({
                "id": item.id,
                "name": item.name,
                "short_name": item.short_name,
                "is_fire_protection": item.is_fire_protection,
                "objects_equipments_count": count,
            })
        return result, total


async def get_all_spec_systems(current_user: User) -> List[dict]:
    await check_permission(current_user, "spec_system_read", "просмотра типов обслуживаемых систем")
    async with new_session() as session:
        items = await spec_system_data.get_spec_system_all(session)
        result = []
        for item in items:
            count = await spec_system_data.count_objects_equipments_by_spec_system(session, item.id)
            result.append({
                "id": item.id,
                "name": item.name,
                "short_name": item.short_name,
                "is_fire_protection": item.is_fire_protection,
                "objects_equipments_count": count,
            })
        return result


async def get_spec_system_options(current_user: User) -> List[Spec_System]:
    await check_permission(current_user, "spec_system_read", "просмотра типов обслуживаемых систем")
    async with new_session() as session:
        return await spec_system_data.get_spec_system_options(session)


# ========== СОЗДАНИЕ ==========

async def create_spec_system(
    payload: SpecSystemCreate,
    current_user: User,
) -> dict:
    await check_permission(current_user, "spec_system_create", "создания типов обслуживаемых систем")
    async with new_session() as session:
        if await spec_system_data.check_spec_system_name_exists(session, payload.name):
            raise HTTPException(
                status_code=400,
                detail=f"Тип обслуживаемой системы с названием '{payload.name}' уже существует",
            )
        spec_system = await spec_system_data.create_spec_system(session, payload)
        return {
            "id": spec_system.id,
            "name": spec_system.name,
            "short_name": spec_system.short_name,
            "is_fire_protection": spec_system.is_fire_protection,
            "objects_equipments_count": 0,
        }


# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_system_with_stats(
    spec_system_id: int,
    payload: SpecSystemUpdate,
    current_user: User,
) -> dict:
    await check_permission(current_user, "spec_system_modify", "изменения типов обслуживаемых систем")
    async with new_session() as session:
        existing = await spec_system_data.get_spec_system_by_id(session, spec_system_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип обслуживаемой системы с id {spec_system_id} не найден",
            )

        if payload.name and payload.name != existing.name:
            if await spec_system_data.check_spec_system_name_exists(session, payload.name, spec_system_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип обслуживаемой системы с названием '{payload.name}' уже существует",
                )

        spec_system = await spec_system_data.update_spec_system(session, spec_system_id, payload)
        count = await spec_system_data.count_objects_equipments_by_spec_system(session, spec_system_id)
        return {
            "id": spec_system.id,
            "name": spec_system.name,
            "short_name": spec_system.short_name,
            "is_fire_protection": spec_system.is_fire_protection,
            "objects_equipments_count": count,
        }


# ========== УДАЛЕНИЕ ==========

async def delete_spec_system(spec_system_id: int, current_user: User) -> bool:
    await check_permission(current_user, "spec_system_delete", "удаления типов обслуживаемых систем")
    async with new_session() as session:
        existing = await spec_system_data.get_spec_system_by_id(session, spec_system_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип обслуживаемой системы с id {spec_system_id} не найден",
            )

        count = await spec_system_data.count_objects_equipments_by_spec_system(session, spec_system_id)
        if count > 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Невозможно удалить тип обслуживаемой системы '{existing.name}': "
                    f"связан с {count} записями оборудования на объектах"
                ),
            )

        return await spec_system_data.delete_spec_system(session, spec_system_id)
