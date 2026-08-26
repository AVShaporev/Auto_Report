"""SaaS-эндпоинт фронт-баннера: текущие лимиты тарифа + master-inbound.

Стояние слоя:
  - На pre-SaaS hi-tech / в dev'е переменные TENANT_*/MAX_* в .env не выставлены.
    Тогда отдаём `plan=null`, `slug=null`, `objects.max=null`, `users.max=null` —
    фронт это интерпретирует как «без лимитов», баннер не показывается.
  - В tenant-инстансах (созданных через provision-tenant.sh) переменные
    прокинуты из .env.sops → отдаём фактические значения. Фронт сравнивает
    used/max и показывает жёлтый/красный баннер.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from config import settings
from database.database import new_session
from data import object as object_data
from data import user as user_data
from model.user import User
from schema.log import LogEntry, LogFilters
from schema.pagination import PaginatedResponse, PaginationParams
from service import log as log_service
from service.auth import get_current_user
from service.master_client import MasterUnavailable, fetch_lifecycle

router = APIRouter(prefix='/api/tenant', tags=['API'])


async def _require_master_token(
    authorization: Optional[str] = Header(None),
) -> None:
    """Guard для master-inbound endpoint'ов. Проверяет что incoming
    `Authorization: Bearer <token>` совпадает с `MASTER_API_TENANT_TOKEN`
    (shared secret между master и тенантом; тот же токен тенант шлёт
    в master для /api/lifecycle/{slug} — используем его в обе стороны)."""
    expected = settings.MASTER_API_TENANT_TOKEN
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MASTER_API_TENANT_TOKEN не сконфигурирован — "
                   "master-inbound endpoints недоступны",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
        )
    token = authorization[len("Bearer "):].strip()
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid master token",
        )


@router.get('/limits')
async def get_tenant_limits(current_user: User = Depends(get_current_user)) -> dict:
    """Текущие лимиты тарифа и использование.

    Доступно любому авторизованному пользователю tenant'а — баннер видят все,
    действие при лимите всё равно ограничено user_create/object_create правами.
    """
    async with new_session() as session:
        objects_used = await object_data.count_objects(session)
        users_used = await user_data.count_users(session)

    return {
        "slug": settings.TENANT_SLUG,
        "plan": settings.TENANT_PLAN,
        "objects": {
            "used": objects_used,
            "max": settings.MAX_OBJECTS,
        },
        "users": {
            "used": users_used,
            "max": settings.MAX_USERS,
        },
    }


@router.get('/tech-logs', response_model=PaginatedResponse[LogEntry])
async def get_tech_logs(
    pagination: PaginationParams = Depends(),
    kind: Optional[str] = Query(None, description="function | http"),
    function: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    path: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    status_code: Optional[int] = Query(None),
    duration_min: Optional[float] = Query(None, ge=0),
    duration_max: Optional[float] = Query(None, ge=0),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    sort_by: str = Query("started_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    _: None = Depends(_require_master_token),
):
    """Технические JSONL-логи для master (Фаза 2 из #312).

    Auth: `Authorization: Bearer <MASTER_API_TENANT_TOKEN>` — тот же
    shared secret что тенант использует в обратную сторону
    (`/api/lifecycle/{slug}` через master_client). Master ходит сюда
    напрямую по публичному URL `https://<slug>.cool-doc.ru/api/tenant/tech-logs`
    и рендерит логи в своей master-UI `TechLogsView`.

    Отдаёт тот же контент что старый `/api/log/list`, но без RBAC-проверки
    на юзерскую сессию (авторизация уже через master-token).
    """
    filters = LogFilters(
        kind=kind, function=function, user=user, module=module,
        path=path, method=method, status_code=status_code,
        duration_min=duration_min, duration_max=duration_max,
        date_from=date_from, date_to=date_to,
        sort_by=sort_by, sort_order=sort_order,
    )
    items, total = await log_service.list_logs_for_master(pagination, filters)
    pages = (total + pagination.limit - 1) // pagination.limit if total else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages,
    )


@router.get('/lifecycle')
async def get_tenant_lifecycle(current_user: User = Depends(get_current_user)) -> dict:
    """Прокси на master `GET /api/lifecycle/{slug}` для soft-mode банера (Этап 8.2).

    Кэшируется 5 минут в памяти (см. service.master_client). Ходит на master
    от имени tenant'а через MASTER_API_TENANT_TOKEN — этот токен НЕ видит фронт.

    503 если:
    - TENANT_SLUG / MASTER_URL / MASTER_API_TENANT_TOKEN не сконфигурированы
      (dev/pre-SaaS hi-tech до раскатки Этапа 8.2 → фронт баннер не показывает).
    - master недоступен и в кэше ничего нет.
    """
    if not settings.TENANT_SLUG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TENANT_SLUG не задан",
        )
    try:
        return await fetch_lifecycle(settings.TENANT_SLUG)
    except MasterUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Master lifecycle недоступен: {exc}",
        )
