"""GET /api/activity_log/list — журнал пользовательских действий (v1.0.14).

Замена LogsView в тенанте. Виден только админам (is_admin).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from model.user import User
from schema.activity_log import ActivityLogResponse
from schema.pagination import PaginationParams, PaginatedResponse
from service import activity_log as activity_log_service
from service.auth import get_current_user


router = APIRouter(prefix="/api/activity_log", tags=["activity_log"])


@router.get("/list", response_model=PaginatedResponse[ActivityLogResponse])
async def get_activity_log_list(
    pagination: PaginationParams = Depends(),
    user_id: Optional[int] = Query(None, description="Фильтр по user_id"),
    entity: Optional[str] = Query(None, description="Фильтр по типу сущности"),
    action: Optional[str] = Query(None, description="Фильтр по типу действия"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None, description="Поиск по summary/user_name (ILIKE)"),
    current_user: User = Depends(get_current_user),
):
    """Только для админов (is_admin + is_superadmin)."""
    if not (current_user.role.is_admin or current_user.role.is_superadmin):
        raise HTTPException(status_code=403, detail="Доступ только для администраторов")

    items, total = await activity_log_service.list_activity_logs(
        user_id=user_id, entity=entity, action=action,
        date_from=date_from, date_to=date_to, search=search,
        skip=pagination.skip, limit=pagination.limit,
    )
    pages = (total + pagination.limit - 1) // pagination.limit if total else 0
    return PaginatedResponse(
        items=[ActivityLogResponse.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages,
    )
