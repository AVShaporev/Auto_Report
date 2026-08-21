"""Mobile-компактные endpoints для PWA/Capacitor-клиента (Mobile M1.3+M1.5).

Все под общим `/api/mobile/*`, все требуют Bearer JWT (существующий
get_current_user из service/auth.py).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

from database.database import new_session
from data import mobile as mobile_data
from model.user import User
from schema.mobile import (
    MobileIssueListItem,
    MobileObjectEquipmentItem,
    MobileObjectSummaryItem,
    MobileOrderListItem,
    MobileReportListItem,
)
from service.auth import get_current_user
from service import mobile_upload as upload_service


router = APIRouter(prefix="/api/mobile", tags=["mobile"])


@router.get("/issues", response_model=List[MobileIssueListItem])
async def mobile_issues(
    only_open: bool = Query(True, description="Только неустранённые"),
    only_mine: bool = Query(True, description="Только назначенные на меня"),
    object_id: Optional[int] = Query(None, description="Drill-down: неисправности по объекту"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
) -> List[MobileIssueListItem]:
    async with new_session() as session:
        rows = await mobile_data.get_issues_mobile_list(
            session,
            user_id=current_user.id,
            only_open=only_open,
            only_mine=only_mine,
            object_id=object_id,
            limit=limit,
        )
    return [MobileIssueListItem(**r) for r in rows]


@router.get("/objects", response_model=List[MobileObjectSummaryItem])
async def mobile_objects(
    contract_id: int | None = Query(None, description="Фильтр по контракту"),
    limit: int = Query(200, ge=1, le=500),
    current_user: User = Depends(get_current_user),
) -> List[MobileObjectSummaryItem]:
    async with new_session() as session:
        rows = await mobile_data.get_objects_mobile_summary(
            session, contract_id=contract_id, limit=limit,
        )
    return [MobileObjectSummaryItem(**r) for r in rows]


@router.get("/reports", response_model=List[MobileReportListItem])
async def mobile_reports(
    only_mine: bool = Query(True),
    object_id: Optional[int] = Query(None, description="Drill-down: отчёты по объекту"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
) -> List[MobileReportListItem]:
    async with new_session() as session:
        rows = await mobile_data.get_reports_mobile_list(
            session,
            user_id=current_user.id,
            only_mine=only_mine,
            object_id=object_id,
            limit=limit,
        )
    return [MobileReportListItem(**r) for r in rows]


# ============================================================================
# M1.5 — Chunked media upload
# ============================================================================

class MobileUploadInitRequest(BaseModel):
    kind: str  # 'issue_photo' | 'report_signature' | 'report_photo' | ...
    filename: str
    total_size: int


class MobileUploadStatusResponse(BaseModel):
    upload_id: str
    kind: str
    filename: str
    total_size: int
    received_bytes: int
    is_complete: bool
    final_path: Optional[str] = None
    max_chunk_size: int
    expires_at: str

    model_config = ConfigDict(from_attributes=False)


def _row_to_status(row) -> MobileUploadStatusResponse:
    return MobileUploadStatusResponse(
        upload_id=row.upload_id,
        kind=row.kind,
        filename=row.filename,
        total_size=row.total_size,
        received_bytes=row.received_bytes,
        is_complete=row.is_complete,
        final_path=row.final_path,
        max_chunk_size=upload_service.MAX_CHUNK_SIZE,
        expires_at=row.expires_at.isoformat(),
    )


@router.post("/media/upload/init", response_model=MobileUploadStatusResponse)
async def mobile_upload_init(
    body: MobileUploadInitRequest,
    current_user: User = Depends(get_current_user),
) -> MobileUploadStatusResponse:
    try:
        row = await upload_service.init_upload_session(
            user_name=current_user.name,
            kind=body.kind,
            filename=body.filename,
            total_size=body.total_size,
        )
    except upload_service.UploadError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return _row_to_status(row)


@router.put("/media/upload/{upload_id}", response_model=MobileUploadStatusResponse)
async def mobile_upload_chunk(
    upload_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> MobileUploadStatusResponse:
    content_range = request.headers.get("content-range")
    if not content_range:
        raise HTTPException(status_code=400, detail="Content-Range header required")
    chunk_bytes = await request.body()
    if not chunk_bytes:
        raise HTTPException(status_code=400, detail="empty body")
    try:
        row = await upload_service.append_chunk(
            upload_id=upload_id,
            user_name=current_user.name,
            content_range=content_range,
            chunk_bytes=chunk_bytes,
        )
        # Если это был последний chunk — сразу финализируем.
        if row.received_bytes >= row.total_size:
            finalized = await upload_service.finalize_if_complete(upload_id=upload_id)
            if finalized is not None:
                row = finalized
    except upload_service.UploadError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return _row_to_status(row)


@router.get("/media/upload/{upload_id}", response_model=MobileUploadStatusResponse)
async def mobile_upload_status(
    upload_id: str,
    current_user: User = Depends(get_current_user),
) -> MobileUploadStatusResponse:
    async with new_session() as session:
        from data import media_upload_session as upload_data
        row = await upload_data.get_media_upload_session(session, upload_id)
    if row is None:
        raise HTTPException(status_code=404, detail="upload session not found")
    if row.user_name != current_user.name:
        raise HTTPException(status_code=403, detail="access denied")
    return _row_to_status(row)


@router.get("/orders", response_model=List[MobileOrderListItem])
async def mobile_orders(
    only_mine: bool = Query(True),
    status_id: Optional[List[int]] = Query(None, description="Мультиселект по spec_order_statuses.id"),
    object_id: Optional[int] = Query(None, description="Drill-down: заявки по объекту"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
) -> List[MobileOrderListItem]:
    async with new_session() as session:
        rows = await mobile_data.get_orders_mobile_list(
            session,
            user_id=current_user.id,
            only_mine=only_mine,
            status_ids=status_id,
            object_id=object_id,
            limit=limit,
        )
    return [MobileOrderListItem(**r) for r in rows]


@router.get("/object-equipment", response_model=List[MobileObjectEquipmentItem])
async def mobile_object_equipment(
    object_id: int = Query(..., ge=1, description="ID объекта, чьё оборудование запрашиваем"),
    limit: int = Query(200, ge=1, le=500),
    current_user: User = Depends(get_current_user),
) -> List[MobileObjectEquipmentItem]:
    """Список единиц оборудования на объекте (drill-down из ObjectDetailView)."""
    async with new_session() as session:
        rows = await mobile_data.get_object_equipment_mobile_list(
            session, object_id=object_id, limit=limit,
        )
    return [MobileObjectEquipmentItem(**r) for r in rows]
