"""DAO для push_tokens (FCM/APNs registration).

Entity-prefix naming — см. [[autoreport-data-layer-naming]].
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from model.push_token import PushToken


async def get_push_token_by_token(
    session: AsyncSession, token: str
) -> Optional[PushToken]:
    q = select(PushToken).where(PushToken.token == token)
    return (await session.execute(q)).scalar_one_or_none()


async def list_push_tokens_for_user(
    session: AsyncSession,
    user_id: int,
    *,
    active_only: bool = True,
) -> List[PushToken]:
    q = select(PushToken).where(PushToken.user_id == user_id)
    if active_only:
        q = q.where(PushToken.is_active.is_(True))
    q = q.order_by(PushToken.last_seen_at.desc())
    return list((await session.execute(q)).scalars().all())


async def upsert_push_token(
    session: AsyncSession,
    *,
    user_id: int,
    platform: str,
    token: str,
    device_id: Optional[str] = None,
    app_version: Optional[str] = None,
) -> PushToken:
    """Upsert по (token, platform). Если токен уже есть — перезаписываем
    user_id/device_id/app_version и обновляем last_seen_at.

    Ситуация: юзер A разлогинился на устройстве, юзер B залогинился —
    FCM/APNs токен один и тот же, но принадлежность юзеру сменилась.
    """
    now = datetime.now(timezone.utc)
    existing = await get_push_token_by_token(session, token)
    if existing is not None:
        existing.user_id = user_id
        existing.platform = platform
        existing.device_id = device_id
        existing.app_version = app_version
        existing.last_seen_at = now
        existing.is_active = True
        await session.commit()
        await session.refresh(existing)
        return existing

    row = PushToken(
        user_id=user_id,
        platform=platform,
        token=token,
        device_id=device_id,
        app_version=app_version,
        last_seen_at=now,
        is_active=True,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def delete_push_token(
    session: AsyncSession, user_id: int, token: str
) -> bool:
    """Клиент выходит из системы или сбрасывает разрешение уведомлений —
    сносим свою запись. Только по совпадению user_id, чтобы юзер A не
    мог удалить регистрацию юзера B."""
    stmt = (
        delete(PushToken)
        .where(PushToken.user_id == user_id)
        .where(PushToken.token == token)
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0


async def cleanup_stale_push_tokens(
    session: AsyncSession, max_age_days: int = 30
) -> int:
    """Cron-задача. Сносит токены, которые не подтверждены (last_seen_at)
    больше max_age_days дней — устройство либо потеряло связь, либо
    приложение удалено. FCM/APNs всё равно перестанут доставлять
    в такие токены."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    stmt = delete(PushToken).where(PushToken.last_seen_at < cutoff)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0
