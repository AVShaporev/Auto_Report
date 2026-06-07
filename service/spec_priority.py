from typing import Optional, List, Tuple
from fastapi import HTTPException

from model.user import User
from model.spec_priority import Spec_Priority
from data import spec_priority as spec_priority_data
from schema.spec_priority import SpecPriorityCreate, SpecPriorityUpdate
from schema.pagination import PaginationParams
from database.database import new_session


async def check_permission(
    current_user: User,
    permission: str,
    action: str = "выполнения операции"
) -> None:
    if not hasattr(current_user.role, permission):
        raise HTTPException(
            status_code=500,
            detail=f"Право {permission} не определено в системе"
        )

    has_permission = getattr(current_user.role, permission)
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=f"Недостаточно прав для {action}"
        )


# ========== ПОЛУЧЕНИЕ ==========

async def get_spec_priority_by_id(
    spec_priority_id: int,
    current_user: User,
    load_issues: bool = False
) -> Spec_Priority:
    await check_permission(current_user, "spec_priority_read", "просмотра приоритетов")

    async with new_session() as session:
        spec_priority = await spec_priority_data.get_spec_priority_by_id(
            session,
            spec_priority_id,
            load_issues=load_issues
        )

        if not spec_priority:
            raise HTTPException(
                status_code=404,
                detail=f"Приоритет с id {spec_priority_id} не найден"
            )

        return spec_priority


async def get_spec_priorities_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc"
) -> Tuple[List[Spec_Priority], int]:
    await check_permission(current_user, "spec_priority_read", "просмотра списка приоритетов")

    async with new_session() as session:
        return await spec_priority_data.get_spec_priority_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_issues=False
        )


async def get_all_spec_priorities(
    current_user: User,
    load_issues: bool = False
) -> List[Spec_Priority]:
    await check_permission(current_user, "spec_priority_read", "просмотра приоритетов")

    async with new_session() as session:
        return await spec_priority_data.get_spec_priority_all(session, load_issues=load_issues)


async def get_spec_priority_options(
    current_user: User
) -> List[Spec_Priority]:
    await check_permission(current_user, "spec_priority_read", "просмотра приоритетов")

    async with new_session() as session:
        return await spec_priority_data.get_spec_priority_options(session)


# ========== СТАТИСТИКА ==========

async def get_spec_priority_with_stats(
    spec_priority_id: int,
    current_user: User
) -> dict:
    await check_permission(current_user, "spec_priority_read", "просмотра приоритетов")

    async with new_session() as session:
        spec_priority = await spec_priority_data.get_spec_priority_by_id(
            session,
            spec_priority_id,
            load_issues=False
        )

        if not spec_priority:
            raise HTTPException(
                status_code=404,
                detail=f"Приоритет с id {spec_priority_id} не найден"
            )

        issues_count = await spec_priority_data.count_issues_by_spec_priority(
            session,
            spec_priority_id
        )

        return {
            "id": spec_priority.id,
            "is_system": spec_priority.is_system,
            "name": spec_priority.name,
            "code": spec_priority.code,
            "description": spec_priority.description,
            "issues_count": issues_count
        }


async def get_spec_priorities_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    await check_permission(current_user, "spec_priority_read", "просмотра списка приоритетов")

    async with new_session() as session:
        items, total = await spec_priority_data.get_spec_priority_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_issues=False
        )

        result_items = []
        for item in items:
            issues_count = await spec_priority_data.count_issues_by_spec_priority(
                session,
                item.id
            )
            result_items.append({
                "id": item.id,
                "is_system": item.is_system,
                "name": item.name,
                "code": item.code,
                "description": item.description,
                "issues_count": issues_count
            })

        return result_items, total


# ========== СОЗДАНИЕ ==========

async def create_spec_priority(
    spec_priority_create: SpecPriorityCreate,
    current_user: User
) -> Spec_Priority:
    await check_permission(current_user, "spec_priority_create", "создания приоритетов")

    async with new_session() as session:
        if await spec_priority_data.check_spec_priority_name_exists(session, spec_priority_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Приоритет с наименованием '{spec_priority_create.name}' уже существует"
            )

        if await spec_priority_data.check_spec_priority_code_exists(session, spec_priority_create.code):
            raise HTTPException(
                status_code=400,
                detail=f"Приоритет с кодом '{spec_priority_create.code}' уже существует"
            )

        return await spec_priority_data.create_spec_priority(session, spec_priority_create)


# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_priority_with_stats(
    spec_priority_id: int,
    spec_priority_update: SpecPriorityUpdate,
    current_user: User
) -> dict:
    await check_permission(current_user, "spec_priority_modify", "изменения приоритетов")

    async with new_session() as session:
        existing = await spec_priority_data.get_spec_priority_by_id(session, spec_priority_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Приоритет с id {spec_priority_id} не найден"
            )

        if spec_priority_update.name and spec_priority_update.name != existing.name:
            if await spec_priority_data.check_spec_priority_name_exists(
                session, spec_priority_update.name, spec_priority_id
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Приоритет с наименованием '{spec_priority_update.name}' уже существует"
                )

        if spec_priority_update.code and spec_priority_update.code != existing.code:
            if await spec_priority_data.check_spec_priority_code_exists(
                session, spec_priority_update.code, spec_priority_id
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Приоритет с кодом '{spec_priority_update.code}' уже существует"
                )

        spec_priority = await spec_priority_data.update_spec_priority(
            session, spec_priority_id, spec_priority_update
        )

        issues_count = await spec_priority_data.count_issues_by_spec_priority(session, spec_priority_id)

        return {
            "id": spec_priority.id,
            "is_system": spec_priority.is_system,
            "name": spec_priority.name,
            "code": spec_priority.code,
            "description": spec_priority.description,
            "issues_count": issues_count
        }


# ========== УДАЛЕНИЕ ==========

async def delete_spec_priority(
    spec_priority_id: int,
    current_user: User
) -> bool:
    await check_permission(current_user, "spec_priority_delete", "удаления приоритетов")

    async with new_session() as session:
        spec_priority = await spec_priority_data.get_spec_priority_by_id(
            session,
            spec_priority_id,
            load_issues=True
        )

        if not spec_priority:
            raise HTTPException(
                status_code=404,
                detail=f"Приоритет с id {spec_priority_id} не найден"
            )

        if spec_priority.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_priority.name}' — она необходима для работы системы."
            )

        if spec_priority.issues and len(spec_priority.issues) > 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Невозможно удалить приоритет '{spec_priority.name}': "
                    f"есть связанные неисправности ({len(spec_priority.issues)} шт.)"
                )
            )

        return await spec_priority_data.delete_spec_priority(session, spec_priority_id)
