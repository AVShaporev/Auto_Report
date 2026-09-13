"""DAO для ActivityLog (v1.0.14).

Пишем ВНУТРИ существующей сессии — activity-запись становится частью
той же транзакции что и основная мутация. Если основная мутация
откатывается — лог тоже. Для читалки — новая сессия из new_session().
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from model.activity_log import ActivityLog


def _jsonify_safe(obj: Any) -> Any:
    """Рекурсивно превращает dict/list в JSON-safe версию.

    asyncpg при INSERT в JSONB не умеет кодировать `date`/`datetime`/
    `Decimal` — падает с `TypeError: Object of type date is not JSON
    serializable`, что помечает всю транзакцию как rolled-back и
    следующие обращения к session бросают PendingRollbackError.
    Реальный инцидент 2026-09-13: update_order с `due_date` в
    payload'е повалил PUT /api/order/{id} с 500. Фикс — предварительно
    прогнать details через этот helper.
    """
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _jsonify_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify_safe(v) for v in obj]
    return obj


async def create_activity_log(
    session: AsyncSession,
    *,
    user_id: Optional[int],
    user_name: str,
    action: str,
    entity: str,
    entity_id: Optional[int],
    summary: str,
    details: Optional[dict[str, Any]] = None,
) -> ActivityLog:
    """Пишет ActivityLog и коммитит сразу.

    Каллер (service/*.py) уже сделал `session.commit()` для основной
    мутации к этому моменту (см. паттерн в data/order.py и т.д.). Наш
    INSERT попадает в НОВУЮ транзакцию, поэтому нужен свой commit —
    иначе закрытие сессии в `async with new_session()` откатит запись.
    """
    row = ActivityLog(
        user_id=user_id,
        user_name=user_name,
        action=action,
        entity=entity,
        entity_id=entity_id,
        summary=summary,
        details=_jsonify_safe(details) if details is not None else None,
    )
    session.add(row)
    await session.commit()
    return row


async def list_activity_logs(
    session: AsyncSession,
    *,
    user_id: Optional[int] = None,
    entity: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[ActivityLog], int]:
    """Фильтры + пагинация. Возвращает (items, total)."""
    conditions = []
    if user_id is not None:
        conditions.append(ActivityLog.user_id == user_id)
    if entity:
        conditions.append(ActivityLog.entity == entity)
    if action:
        conditions.append(ActivityLog.action == action)
    if date_from:
        conditions.append(ActivityLog.created_at >= date_from)
    if date_to:
        conditions.append(ActivityLog.created_at <= date_to)
    if search:
        # ILIKE по summary + user_name — юзер-читаемый быстрый поиск.
        pat = f"%{search}%"
        conditions.append(
            (ActivityLog.summary.ilike(pat)) | (ActivityLog.user_name.ilike(pat))
        )
    where = and_(*conditions) if conditions else None

    total_stmt = select(func.count(ActivityLog.id))
    if where is not None:
        total_stmt = total_stmt.where(where)
    total = (await session.execute(total_stmt)).scalar_one()

    items_stmt = (
        select(ActivityLog)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .offset(skip).limit(limit)
    )
    if where is not None:
        items_stmt = items_stmt.where(where)
    items = (await session.execute(items_stmt)).scalars().all()
    return list(items), total
