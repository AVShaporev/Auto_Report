from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from model.report_attachment import Report_Attachment


async def get_report_attachment_by_id(
    session: AsyncSession,
    attachment_id: int,
    *,
    load_uploader: bool = False,
) -> Optional[Report_Attachment]:
    query = select(Report_Attachment).where(Report_Attachment.id == attachment_id)
    if load_uploader:
        query = query.options(selectinload(Report_Attachment.uploader))
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_report_attachment_by_report(
    session: AsyncSession,
    report_id: int,
) -> List[Report_Attachment]:
    query = (
        select(Report_Attachment)
        .where(Report_Attachment.report_id == report_id)
        .options(selectinload(Report_Attachment.uploader))
        .order_by(Report_Attachment.created_at.asc(), Report_Attachment.id.asc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def create_report_attachment(
    session: AsyncSession,
    *,
    report_id: int,
    kind: str,
    title: Optional[str],
    size_bytes: int,
    pages: int,
    uploaded_by: int,
) -> Report_Attachment:
    """
    Создать запись о вложении. pdf_path заполняется отдельным вызовом
    set_report_attachment_path после того, как файл успешно положен на диск
    (нужен id, чтобы построить имя).
    """
    attachment = Report_Attachment(
        report_id=report_id,
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


async def set_report_attachment_path(
    session: AsyncSession,
    attachment_id: int,
    pdf_path: str,
) -> None:
    attachment = await get_report_attachment_by_id(session, attachment_id)
    if attachment:
        attachment.pdf_path = pdf_path
        await session.flush()


async def delete_report_attachment(
    session: AsyncSession, attachment_id: int
) -> Optional[Report_Attachment]:
    attachment = await get_report_attachment_by_id(session, attachment_id)
    if not attachment:
        return None
    await session.delete(attachment)
    return attachment
