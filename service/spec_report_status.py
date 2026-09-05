from typing import List, Optional, Tuple

from fastapi import HTTPException

from model.user import User
from model.spec_report_status import Spec_Report_Status
from data import spec_report_status as spec_report_status_data
from schema.spec_report_status import SpecReportStatusCreate, SpecReportStatusUpdate
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


def _to_response(row: Spec_Report_Status, reports_count: int = 0) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "is_default": row.is_default,
        "reports_count": reports_count,
    }


# ========== ПОЛУЧЕНИЕ ==========

async def get_spec_report_status_options(current_user: User) -> List[Spec_Report_Status]:
    """Options — требует spec_report_status_read.

    Юзеру без этого права селект статусов отчёта не показываем. Создание
    отчёта без выбранного статуса — бэк подставит is_default (см.
    data.create_report)."""
    await check_permission(current_user, "spec_report_status_read", "просмотра статусов отчётов")

    async with new_session() as session:
        return await spec_report_status_data.get_spec_report_status_all(session)


async def get_spec_report_status_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> Tuple[List[dict], int]:
    await check_permission(current_user, "spec_report_status_read", "просмотра справочника статусов отчётов")

    async with new_session() as session:
        items, total = await spec_report_status_data.get_spec_report_status_paginated(
            session, skip=pagination.skip, limit=pagination.limit,
            search=search, sort_by=sort_by, sort_order=sort_order,
        )
        result = []
        for item in items:
            reports_count = await spec_report_status_data.count_reports_by_status(session, item.id)
            result.append(_to_response(item, reports_count))
        return result, total


async def get_spec_report_status_with_stats(
    spec_report_status_id: int, current_user: User
) -> dict:
    await check_permission(current_user, "spec_report_status_read", "просмотра справочника статусов отчётов")

    async with new_session() as session:
        row = await spec_report_status_data.get_spec_report_status_by_id(session, spec_report_status_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Статус с id {spec_report_status_id} не найден")
        reports_count = await spec_report_status_data.count_reports_by_status(session, spec_report_status_id)
        return _to_response(row, reports_count)


# ========== СОЗДАНИЕ ==========

async def create_spec_report_status(
    payload: SpecReportStatusCreate, current_user: User
) -> dict:
    await check_permission(current_user, "spec_report_status_create", "создания статусов отчётов")

    async with new_session() as session:
        if await spec_report_status_data.check_name_exists(session, payload.name):
            raise HTTPException(status_code=400, detail=f"Статус с именем '{payload.name}' уже существует")

        row = await spec_report_status_data.create_spec_report_status(session, payload)
        return _to_response(row, reports_count=0)


# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_report_status(
    spec_report_status_id: int, payload: SpecReportStatusUpdate, current_user: User
) -> dict:
    await check_permission(current_user, "spec_report_status_modify", "изменения статусов отчётов")

    async with new_session() as session:
        existing = await spec_report_status_data.get_spec_report_status_by_id(session, spec_report_status_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Статус с id {spec_report_status_id} не найден")

        if payload.name and payload.name != existing.name:
            if await spec_report_status_data.check_name_exists(session, payload.name, exclude_id=spec_report_status_id):
                raise HTTPException(status_code=400, detail=f"Статус с именем '{payload.name}' уже существует")

        if payload.is_default is False and existing.is_default:
            raise HTTPException(
                status_code=400,
                detail="Нельзя снять флаг 'по умолчанию' — сначала назначьте другой статус дефолтным.",
            )

        row = await spec_report_status_data.update_spec_report_status(
            session, spec_report_status_id, payload
        )
        reports_count = await spec_report_status_data.count_reports_by_status(session, spec_report_status_id)
        return _to_response(row, reports_count)


# ========== УДАЛЕНИЕ ==========

async def delete_spec_report_status(
    spec_report_status_id: int, current_user: User
) -> bool:
    await check_permission(current_user, "spec_report_status_delete", "удаления статусов отчётов")

    async with new_session() as session:
        row = await spec_report_status_data.get_spec_report_status_by_id(session, spec_report_status_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Статус с id {spec_report_status_id} не найден")

        if row.is_default:
            raise HTTPException(
                status_code=400,
                detail="Нельзя удалить статус, помеченный 'по умолчанию' — сначала назначьте другой дефолтным.",
            )

        reports_count = await spec_report_status_data.count_reports_by_status(session, spec_report_status_id)
        if reports_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Нельзя удалить статус '{row.name}': используется в {reports_count} отчётах.",
            )

        return await spec_report_status_data.delete_spec_report_status(session, spec_report_status_id)
