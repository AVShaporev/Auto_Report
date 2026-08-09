"""DAO для media_upload_sessions (Mobile M1.5 chunked upload).

Entity-prefix naming (см. autoreport-data-layer-naming).
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from model.media_upload_session import MediaUploadSession


async def create_media_upload_session(
    session: AsyncSession,
    *,
    upload_id: str,
    user_name: str,
    kind: str,
    filename: str,
    total_size: int,
    tmp_path: str,
    expires_at: datetime,
) -> MediaUploadSession:
    row = MediaUploadSession(
        upload_id=upload_id,
        user_name=user_name,
        kind=kind,
        filename=filename,
        total_size=total_size,
        received_bytes=0,
        tmp_path=tmp_path,
        expires_at=expires_at,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_media_upload_session(
    session: AsyncSession, upload_id: str
) -> Optional[MediaUploadSession]:
    stmt = select(MediaUploadSession).where(
        MediaUploadSession.upload_id == upload_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_media_upload_progress(
    session: AsyncSession,
    row: MediaUploadSession,
    *,
    received_bytes: int,
) -> None:
    # updated_at не трогаем — Base.updated_at имеет onupdate=datetime.now
    # (naive), сработает автоматом. Ручное `datetime.now(timezone.utc)` ломало
    # asyncpg: колонка через Base типизирована как TIMESTAMP WITHOUT TIME ZONE,
    # aware datetime не биндится и падает DataError "can't subtract
    # offset-naive and offset-aware datetimes" (M5.3 hotfix).
    row.received_bytes = received_bytes
    await session.commit()


async def finalize_media_upload_session(
    session: AsyncSession,
    row: MediaUploadSession,
    *,
    final_path: str,
) -> None:
    row.final_path = final_path
    row.is_complete = True
    await session.commit()


async def cleanup_expired_media_upload_sessions(
    session: AsyncSession,
) -> list[str]:
    """Возвращает список tmp_path'ов, которые надо удалить с диска."""
    now = datetime.now(timezone.utc)
    stmt = select(MediaUploadSession).where(
        MediaUploadSession.expires_at < now
    ).where(MediaUploadSession.is_complete.is_(False))
    rows = list((await session.execute(stmt)).scalars().all())
    tmp_paths = [r.tmp_path for r in rows]
    if rows:
        await session.execute(
            delete(MediaUploadSession).where(
                MediaUploadSession.id.in_([r.id for r in rows])
            )
        )
        await session.commit()
    return tmp_paths
