"""Mobile-компактные endpoints для PWA/Capacitor-клиента (Mobile M1.3+M1.5).

Все под общим `/api/mobile/*`, все требуют Bearer JWT (существующий
get_current_user из service/auth.py).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from database.database import new_session
from data import mobile as mobile_data
from model.user import User
from schema.mobile import (
    MobileIssueListItem,
    MobileObjectEquipmentDetail,
    MobileObjectEquipmentItem,
    MobileObjectSummaryItem,
    MobileOrderListItem,
    MobileReportListItem,
)
from schema.object import ObjectResponse
from schema.order import OrderResponse
from schema.report import ReportResponse
from service.auth import get_current_user
from service import mobile_upload as upload_service
from service import object as object_service
from service import order as order_service
from service import report as report_service


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


# ============================================================================
# Bulk-details endpoints для mobile-prefetch (Phase 3 шаг 3+)
# ============================================================================
# При sync мобилка тянет ПОЛНЫЕ детали всех заявок/связанных объектов/своих
# отчётов одним запросом на сущность — чтобы в offline инженер мог открыть
# любую заявку/объект/отчёт, даже те что до выезда не открывал вручную.
#
# Форма запроса: POST c body {ids: [1,2,3]} — GET с ids в URL режется по
# длине URL при 200+ элементах, POST безопаснее. Пустой список → пустой
# ответ. Один не найденный/без прав элемент — тихо пропускаем (лишний
# «404» не рушит sync остальных).
#
# Внутри — цикл по существующим сервисам (get_order_with_details, etc.);
# каждый вызов открывает свою async-сессию. Overhead на 100 ID — секунды,
# приемлемо для sync (юзер жмёт «Обновить» и ждёт прогресс-бар).


class _BulkIdsRequest(BaseModel):
    ids: List[int] = Field(default_factory=list, description="ID сущностей для bulk-details")


@router.post("/orders/bulk-details", response_model=List[OrderResponse])
async def mobile_orders_bulk_details(
    body: _BulkIdsRequest,
    current_user: User = Depends(get_current_user),
) -> List[OrderResponse]:
    if not body.ids:
        return []
    results: List[OrderResponse] = []
    for order_id in body.ids:
        try:
            item = await order_service.get_order_with_details(order_id, current_user)
            results.append(item)
        except HTTPException:
            # 404 / 403 по одному ID — не рушим sync остальных.
            continue
    return results


@router.post("/objects/bulk-details", response_model=List[ObjectResponse])
async def mobile_objects_bulk_details(
    body: _BulkIdsRequest,
    current_user: User = Depends(get_current_user),
) -> List[ObjectResponse]:
    if not body.ids:
        return []
    results: List[ObjectResponse] = []
    for object_id in body.ids:
        try:
            item = await object_service.get_object_with_stats(object_id, current_user)
            results.append(item)
        except HTTPException:
            continue
    return results


@router.post("/reports/bulk-details", response_model=List[ReportResponse])
async def mobile_reports_bulk_details(
    body: _BulkIdsRequest,
    current_user: User = Depends(get_current_user),
) -> List[ReportResponse]:
    if not body.ids:
        return []
    results: List[ReportResponse] = []
    for report_id in body.ids:
        try:
            item = await report_service.get_report_by_id(
                report_id, current_user, load_relations=True,
            )
            results.append(item)
        except HTTPException:
            continue
    return results


@router.get("/object-equipment/{oe_id}", response_model=MobileObjectEquipmentDetail)
async def mobile_object_equipment_detail(
    oe_id: int,
    current_user: User = Depends(get_current_user),
) -> MobileObjectEquipmentDetail:
    """Деталь единицы оборудования для mobile-drill-down.

    Без RBAC-проверки: у инженерской роли часто нет `object_equipment_read`,
    а тап на карточку в списке оборудования на объекте должен открывать
    детали. Общий Bearer JWT достаточно.
    """
    async with new_session() as session:
        row = await mobile_data.get_object_equipment_mobile_detail(
            session, object_equipment_id=oe_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Единица оборудования не найдена")
    return MobileObjectEquipmentDetail(**row)


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
