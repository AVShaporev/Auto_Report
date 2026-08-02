"""DAO для idempotency_keys.

Entity-prefix naming (см. autoreport-data-layer-naming).
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from model.idempotency_key import IdempotencyKey


async def get_idempotency_key(
    session: AsyncSession, *, user_name: str, key: str
) -> Optional[IdempotencyKey]:
    """Найти НЕпросроченную запись. Просроченные игнорируем — cleanup-cron
    их удалит, но клиент к тому времени уже может ретаить с новым ключом."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(IdempotencyKey)
        .where(IdempotencyKey.user_name == user_name)
        .where(IdempotencyKey.key == key)
        .where(IdempotencyKey.expires_at > now)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_idempotency_key(
    session: AsyncSession,
    *,
    user_name: str,
    key: str,
    method: str,
    path: str,
    status_code: int,
    response_body: bytes,
    response_headers: Optional[Dict[str, Any]] = None,
    ttl_hours: int = 24,
) -> IdempotencyKey:
    row = IdempotencyKey(
        user_name=user_name,
        key=key,
        method=method,
        path=path,
        status_code=status_code,
        response_body=response_body,
        response_headers=response_headers,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    )
    session.add(row)
    await session.commit()
    return row


async def cleanup_expired_idempotency_keys(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    stmt = delete(IdempotencyKey).where(IdempotencyKey.expires_at <= now)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0
