from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from model.issue_attachment import Issue_Attachment


async def get_issue_attachment_by_id(
    session: AsyncSession,
    attachment_id: int,
    *,
    load_uploader: bool = False,
) -> Optional[Issue_Attachment]:
    query = select(Issue_Attachment).where(Issue_Attachment.id == attachment_id)
    if load_uploader:
        query = query.options(selectinload(Issue_Attachment.uploader))
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_issue_attachment_by_issue(
    session: AsyncSession,
    issue_id: int,
) -> List[Issue_Attachment]:
    query = (
        select(Issue_Attachment)
        .where(Issue_Attachment.issue_id == issue_id)
        .options(selectinload(Issue_Attachment.uploader))
        .order_by(Issue_Attachment.created_at.asc(), Issue_Attachment.id.asc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def create_issue_attachment(
    session: AsyncSession,
    *,
    issue_id: int,
    kind: str,
    title: Optional[str],
    size_bytes: int,
    pages: int,
    uploaded_by: int,
) -> Issue_Attachment:
    """
    Создать запись о вложении. pdf_path заполняется отдельным вызовом
    set_issue_attachment_path после того, как файл успешно положен на диск
    (нужен id, чтобы построить имя).
    """
    attachment = Issue_Attachment(
        issue_id=issue_id,
        kind=kind,
        title=title,
        pdf_path="",  # будет заполнено после записи файла на диск
        size_bytes=size_bytes,
        pages=pages,
        uploaded_by=uploaded_by,
    )
    session.add(attachment)
    await session.flush()  # получаем id
    return attachment


async def set_issue_attachment_path(
    session: AsyncSession,
    attachment_id: int,
    pdf_path: str,
) -> None:
    attachment = await get_issue_attachment_by_id(session, attachment_id)
    if attachment:
        attachment.pdf_path = pdf_path
        await session.flush()


async def delete_issue_attachment(
    session: AsyncSession, attachment_id: int
) -> Optional[Issue_Attachment]:
    attachment = await get_issue_attachment_by_id(session, attachment_id)
    if not attachment:
        return None
    await session.delete(attachment)
    return attachment
