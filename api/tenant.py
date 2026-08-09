"""SaaS-эндпоинт фронт-баннера: текущие лимиты тарифа.

Стояние слоя:
  - На pre-SaaS hi-tech / в dev'е переменные TENANT_*/MAX_* в .env не выставлены.
    Тогда отдаём `plan=null`, `slug=null`, `objects.max=null`, `users.max=null` —
    фронт это интерпретирует как «без лимитов», баннер не показывается.
  - В tenant-инстансах (созданных через provision-tenant.sh) переменные
    прокинуты из .env.sops → отдаём фактические значения. Фронт сравнивает
    used/max и показывает жёлтый/красный баннер.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from config import settings
from database.database import new_session
from data import object as object_data
from data import user as user_data
from model.user import User
from service.auth import get_current_user
from service.master_client import MasterUnavailable, fetch_lifecycle

router = APIRouter(prefix='/api/tenant', tags=['API'])


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
