from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime

from model.user import User
from schema.log import LogEntry, LogFilters
from schema.pagination import PaginationParams, PaginatedResponse
from service import log as log_service
from core.dependencies import get_current_active_user


router = APIRouter(prefix="/api/log", tags=["log"])


@router.get("/list", response_model=PaginatedResponse[LogEntry])
async def get_log_list(
    pagination: PaginationParams = Depends(),
    kind: Optional[str] = Query(None, description="function | http"),
    function: Optional[str] = Query(None, description="Подстрока в имени функции"),
    user: Optional[str] = Query(None, description="Подстрока в имени пользователя"),
    module: Optional[str] = Query(None, description="Подстрока в модуле"),
    path: Optional[str] = Query(None, description="Подстрока в HTTP-пути"),
    method: Optional[str] = Query(None, description="HTTP-метод"),
    status_code: Optional[int] = Query(None, description="HTTP-код"),
    duration_min: Optional[float] = Query(None, ge=0, description="Длительность >= сек"),
    duration_max: Optional[float] = Query(None, ge=0, description="Длительность <= сек"),
    date_from: Optional[datetime] = Query(None, description="started_at >="),
    date_to: Optional[datetime] = Query(None, description="started_at <="),
    sort_by: str = Query("started_at", description="started_at | duration_sec | function | user | kind"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Список логов (read-only). Доступ: только администраторы и суперадмины.
    Источник — JSONL-файлы `logs/logs_<Пн>-<Вс>.json`.
    """
    filters = LogFilters(
        kind=kind,
        function=function,
        user=user,
        module=module,
        path=path,
        method=method,
        status_code=status_code,
        duration_min=duration_min,
        duration_max=duration_max,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items, total = await log_service.list_logs(pagination, filters, current_user)

    pages = (total + pagination.limit - 1) // pagination.limit if total else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages,
    )
