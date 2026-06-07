from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_status import Spec_Status
from data import spec_status as spec_status_data
from schema.spec_status import SpecStatusCreate, SpecStatusUpdate
from schema.pagination import PaginationParams
from database.database import new_session

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def check_permission(
    current_user: User,
    permission: str,
    action: str = "выполнения операции"
) -> None:
    """Проверка наличия права у пользователя"""
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

async def get_spec_status_by_id(
    spec_status_id: int,
    current_user: User,
    load_issues: bool = False
) -> Spec_Status:
    """Получить статус по ID с проверкой прав"""
    await check_permission(current_user, "spec_status_read", "просмотра статусов")

    async with new_session() as session:
        spec_status = await spec_status_data.get_spec_status_by_id(
            session,
            spec_status_id,
            load_issues=load_issues
        )

        if not spec_status:
            raise HTTPException(
                status_code=404,
                detail=f"Статус с id {spec_status_id} не найден"
            )

        return spec_status

async def get_spec_statuses_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Spec_Status], int]:
    """Получить список статусов с пагинацией"""
    await check_permission(current_user, "spec_status_read", "просмотра списка статусов")

    async with new_session() as session:
        items, total = await spec_status_data.get_spec_status_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_issues=False
        )

        return items, total

async def get_all_spec_statuses(
    current_user: User,
    load_issues: bool = False
) -> List[Spec_Status]:
    """Получить все статусы"""
    await check_permission(current_user, "spec_status_read", "просмотра статусов")

    async with new_session() as session:
        return await spec_status_data.get_spec_status_all(session, load_issues=load_issues)

async def get_spec_status_options(
    current_user: User
) -> List[Spec_Status]:
    """Получить минимальную информацию о статусах для выпадающих списков"""
    await check_permission(current_user, "spec_status_read", "просмотра статусов")

    async with new_session() as session:
        return await spec_status_data.get_spec_status_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_status_with_stats(
    spec_status_id: int,
    current_user: User
) -> dict:
    """Получить статус со статистикой для ответа"""
    await check_permission(current_user, "spec_status_read", "просмотра статусов")

    async with new_session() as session:
        spec_status = await spec_status_data.get_spec_status_by_id(
            session,
            spec_status_id,
            load_issues=False
        )

        if not spec_status:
            raise HTTPException(
                status_code=404,
                detail=f"Статус с id {spec_status_id} не найден"
            )

        issues_count = await spec_status_data.count_issues_by_spec_status(
            session,
            spec_status_id
        )

        return {
            "id": spec_status.id,
            "name": spec_status.name,
            "code": spec_status.code,
            "issues_count": issues_count
        }

async def update_spec_status_with_stats(
    spec_status_id: int,
    spec_status_update: SpecStatusUpdate,
    current_user: User
) -> dict:
    """Обновить статус и вернуть словарь со статистикой для ответа"""
    await check_permission(current_user, "spec_status_modify", "изменения статусов")

    async with new_session() as session:
        existing = await spec_status_data.get_spec_status_by_id(session, spec_status_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Статус с id {spec_status_id} не найден"
            )

        if spec_status_update.name and spec_status_update.name != existing.name:
            if await spec_status_data.check_spec_status_name_exists(session, spec_status_update.name, spec_status_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Статус с наименованием '{spec_status_update.name}' уже существует"
                )

        if spec_status_update.code and spec_status_update.code != existing.code:
            if await spec_status_data.check_spec_status_code_exists(session, spec_status_update.code, spec_status_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Статус с кодом '{spec_status_update.code}' уже существует"
                )

        spec_status = await spec_status_data.update_spec_status(session, spec_status_id, spec_status_update)

        issues_count = await spec_status_data.count_issues_by_spec_status(session, spec_status_id)

        return {
            "id": spec_status.id,
            "name": spec_status.name,
            "code": spec_status.code,
            "issues_count": issues_count
        }

async def get_spec_statuses_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """Получить список статусов со статистикой для ответа"""
    await check_permission(current_user, "spec_status_read", "просмотра списка статусов")

    async with new_session() as session:
        items, total = await spec_status_data.get_spec_status_paginated(
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
            issues_count = await spec_status_data.count_issues_by_spec_status(
                session,
                item.id
            )
            result_items.append({
                "id": item.id,
                "name": item.name,
                "code": item.code,
                "issues_count": issues_count
            })

        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_status(
    spec_status_create: SpecStatusCreate,
    current_user: User
) -> Spec_Status:
    """Создать новый статус"""
    await check_permission(current_user, "spec_status_create", "создания статусов")

    async with new_session() as session:
        if await spec_status_data.check_spec_status_name_exists(session, spec_status_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Статус с наименованием '{spec_status_create.name}' уже существует"
            )

        if await spec_status_data.check_spec_status_code_exists(session, spec_status_create.code):
            raise HTTPException(
                status_code=400,
                detail=f"Статус с кодом '{spec_status_create.code}' уже существует"
            )

        spec_status = await spec_status_data.create_spec_status(session, spec_status_create)

        return spec_status

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_status(
    spec_status_id: int,
    spec_status_update: SpecStatusUpdate,
    current_user: User
) -> Spec_Status:
    """Обновить статус"""
    await check_permission(current_user, "spec_status_modify", "изменения статусов")

    async with new_session() as session:
        existing = await spec_status_data.get_spec_status_by_id(session, spec_status_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Статус с id {spec_status_id} не найден"
            )

        if spec_status_update.name and spec_status_update.name != existing.name:
            if await spec_status_data.check_spec_status_name_exists(session, spec_status_update.name, spec_status_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Статус с наименованием '{spec_status_update.name}' уже существует"
                )

        if spec_status_update.code and spec_status_update.code != existing.code:
            if await spec_status_data.check_spec_status_code_exists(session, spec_status_update.code, spec_status_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Статус с кодом '{spec_status_update.code}' уже существует"
                )

        spec_status = await spec_status_data.update_spec_status(session, spec_status_id, spec_status_update)

        return spec_status

# ========== УДАЛЕНИЕ ==========

async def delete_spec_status(
    spec_status_id: int,
    current_user: User
) -> bool:
    """Удалить статус"""
    await check_permission(current_user, "spec_status_delete", "удаления статусов")

    async with new_session() as session:
        spec_status = await spec_status_data.get_spec_status_by_id(
            session,
            spec_status_id,
            load_issues=True
        )

        if not spec_status:
            raise HTTPException(
                status_code=404,
                detail=f"Статус с id {spec_status_id} не найден"
            )

        if spec_status.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_status.name}' — она необходима для работы системы."
            )

        if spec_status.issues and len(spec_status.issues) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить статус '{spec_status.name}': есть связанные неисправности ({len(spec_status.issues)} шт.)"
            )

        success = await spec_status_data.delete_spec_status(session, spec_status_id)

        return success
