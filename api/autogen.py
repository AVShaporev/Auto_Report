"""API для авто-генерации заявок (admin-only).

Эндпоинт POST /api/autogen/tick — синхронно вызывает tick_planned_orders,
возвращает счётчики/ошибки. Удобно для проверки на stage без ожидания
cron'а в 00:30 МСК.

Доступ — только для superadmin.
"""
from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_current_active_user
from model.user import User
from service.order_autogen import tick_planned_orders


router = APIRouter(prefix="/api/autogen", tags=["autogen"])


def _require_superadmin(current_user: User = Depends(get_current_active_user)) -> User:
    if not getattr(current_user.role, "is_superadmin", False):
        raise HTTPException(
            status_code=403,
            detail="Только superadmin может вручную запускать tick авто-генерации.",
        )
    return current_user


@router.post("/tick")
async def run_autogen_tick(
    current_user: User = Depends(_require_superadmin),
) -> dict:
    """Запустить tick_planned_orders прямо сейчас. Возвращает счётчики и список ошибок."""
    result = await tick_planned_orders()
    return {
        "summary": result.summary(),
        "objects_total": result.objects_total,
        "orders_created": result.orders_created,
        "orders_already_exist": result.orders_already_exist,
        "objects_skipped_no_period_code": result.objects_skipped_no_period_code,
        "objects_skipped_no_contract": result.objects_skipped_no_contract,
        "errors": result.errors,
    }
