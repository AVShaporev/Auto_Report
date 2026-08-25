"""Service-слой для ActivityLog + helper `log_activity`.

Использование в существующих сервисах:

    from service.activity_log import log_activity
    ...
    await log_activity(
        session, current_user,
        action='create', entity='order', entity_id=order.id,
        summary=f'Создал заявку №{order.number}',
    )

- session — та же, в которой идёт основная мутация. Логи попадают в
  тот же commit; если мутация роллбэкнется — лог тоже.
- current_user — берётся из Depends(get_current_active_user). Может быть
  None для системных действий (autogen, cron) — тогда user_id=None,
  user_name='system'.
- Ошибка вставки лога тихо глотается (loguru.warning): мы не хотим
  ронять успешную мутацию из-за проблем с журналом. Транзакция при
  этом продолжается — SQLAlchemy откатит только сам ActivityLog.
"""
from typing import Any, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from data import activity_log as activity_log_data
from database.database import new_session
from model.activity_log import ActivityLog
from model.user import User


async def log_activity(
    session: AsyncSession,
    user: Optional[User],
    *,
    action: str,
    entity: str,
    entity_id: Optional[int],
    summary: str,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Записать пользовательское действие. Ошибки не пробрасываем."""
    try:
        await activity_log_data.create_activity_log(
            session,
            user_id=user.id if user else None,
            user_name=(user.name if user else "system"),
            action=action,
            entity=entity,
            entity_id=entity_id,
            summary=summary[:500],
            details=details,
        )
    except Exception as e:  # noqa: BLE001 — лог не должен ронять мутацию
        logger.warning(
            "activity_log: failed to write action={} entity={} entity_id={}: {}",
            action, entity, entity_id, e,
        )


async def list_activity_logs(
    *,
    user_id: Optional[int] = None,
    entity: Optional[str] = None,
    action: Optional[str] = None,
    date_from=None,
    date_to=None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """Читалка для API. Использует свою сессию."""
    async with new_session() as session:
        return await activity_log_data.list_activity_logs(
            session,
            user_id=user_id, entity=entity, action=action,
            date_from=date_from, date_to=date_to, search=search,
            skip=skip, limit=limit,
        )
