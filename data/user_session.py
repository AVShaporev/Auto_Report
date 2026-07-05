"""DAO для user_sessions.

Все имена функций с entity-префиксом `user_session_` — см.
[[autoreport-data-layer-naming]] в memory.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from model.user_session import UserSession


async def create_user_session(
    session: AsyncSession,
    *,
    user_id: int,
    refresh_jti: str,
    expires_at: datetime,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    device_info: Optional[Dict[str, Any]] = None,
    geo_country: Optional[str] = None,
) -> UserSession:
    row = UserSession(
        user_id=user_id,
        refresh_jti=refresh_jti,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        device_info=device_info,
        geo_country=geo_country,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_user_session_by_jti(
    session: AsyncSession, refresh_jti: str
) -> Optional[UserSession]:
    q = select(UserSession).where(UserSession.refresh_jti == refresh_jti)
    return (await session.execute(q)).scalar_one_or_none()


async def get_user_session_by_id(
    session: AsyncSession, session_id: int
) -> Optional[UserSession]:
    q = select(UserSession).where(UserSession.id == session_id)
    return (await session.execute(q)).scalar_one_or_none()


async def list_user_sessions_for_user(
    session: AsyncSession,
    user_id: int,
    *,
    active_only: bool = True,
) -> List[UserSession]:
    q = select(UserSession).where(UserSession.user_id == user_id)
    if active_only:
        now = datetime.now(timezone.utc)
        q = q.where(UserSession.revoked_at.is_(None)).where(UserSession.expires_at > now)
    q = q.order_by(UserSession.updated_at.desc())
    return list((await session.execute(q)).scalars().all())


async def touch_user_session(
    session: AsyncSession, session_row: UserSession
) -> None:
    """Обновить last-used-at (updated_at из Base). Полезно на /refresh — но
    у нас там rotate, поэтому в основном используется для fallback-веток."""
    session_row.updated_at = datetime.now(timezone.utc)
    await session.commit()


async def revoke_user_session(
    session: AsyncSession, session_row: UserSession
) -> None:
    if session_row.revoked_at is None:
        session_row.revoked_at = datetime.now(timezone.utc)
        await session.commit()


async def revoke_user_session_by_jti(
    session: AsyncSession, refresh_jti: str
) -> bool:
    row = await get_user_session_by_jti(session, refresh_jti)
    if not row or row.revoked_at is not None:
        return False
    row.revoked_at = datetime.now(timezone.utc)
    await session.commit()
    return True


async def revoke_all_user_sessions(
    session: AsyncSession, user_id: int
) -> int:
    """Помечает revoked_at=NOW() у всех активных сессий юзера. Возвращает
    количество затронутых строк."""
    now = datetime.now(timezone.utc)
    stmt = (
        update(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0
