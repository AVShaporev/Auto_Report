"""SaaS-эндпоинт фронт-баннера: текущие лимиты тарифа.

Стояние слоя:
  - На pre-SaaS hi-tech / в dev'е переменные TENANT_*/MAX_* в .env не выставлены.
    Тогда отдаём `plan=null`, `slug=null`, `objects.max=null`, `users.max=null` —
    фронт это интерпретирует как «без лимитов», баннер не показывается.
  - В tenant-инстансах (созданных через provision-tenant.sh) переменные
    прокинуты из .env.sops → отдаём фактические значения. Фронт сравнивает
    used/max и показывает жёлтый/красный баннер.
"""
from fastapi import APIRouter, Depends

from config import settings
from database.database import new_session
from data import object as object_data
from data import user as user_data
from model.user import User
from service.auth import get_current_user

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
