import io
import re
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

from model.user import User
from schema.order import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderListResponse,
    OrderOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import order as order_service
from service.order_pdf import render_order_pdf, render_order_primary_pdf, render_order_defect_pdf
from service.render_docx import render_order_document, build_attachment_headers
from core.dependencies import get_current_active_user


class BulkPdfRequest(BaseModel):
    """Тело запроса для массового скачивания PDF-актов по заявкам."""
    order_ids: List[int] = Field(..., min_length=1, max_length=200,
                                  description="ID заявок (1..200 за раз)")
    kind: str = Field("to", description="Тип акта: 'to' (плановый), 'primary' (первичный) или 'defect' (дефектовка)")


def _safe_zip_name(name: str) -> str:
    # Минимальная санация: убираем символы, опасные для имени файла в ZIP/файловой системе
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip().strip(".") or "file.pdf"

router = APIRouter(prefix="/api/order", tags=["order"])

@router.get("/list", response_model=PaginatedResponse[OrderListResponse])
async def get_order_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по номеру или описанию"),
    spec_order_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу заявки"),
    contract_id: Optional[int] = Query(None, ge=1, description="Фильтр по контракту"),
    object_id: Optional[int] = Query(None, ge=1, description="Фильтр по объекту"),
    user_id: Optional[int] = Query(None, ge=1, description="Фильтр по пользователю"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    date_from: Optional[date] = Query(None, description="Дата создания с"),
    date_to: Optional[date] = Query(None, description="Дата создания по"),
    region_id: Optional[List[int]] = Query(None, description="Фильтр по регионам объекта (можно несколько)"),
    arial_id: Optional[List[int]] = Query(None, description="Фильтр по районам объекта (можно несколько)"),
    locality_id: Optional[List[int]] = Query(None, description="Фильтр по нас. пунктам объекта (можно несколько)"),
    street_id: Optional[List[int]] = Query(None, description="Фильтр по улицам объекта (можно несколько)"),
    sort_by: str = Query("created_at", description="Поле сортировки"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список заявок с пагинацией

    Требуется право: order_read
    """
    items, total = await order_service.get_orders_paginated_with_details(
        pagination=pagination,
        current_user=current_user,
        search=search,
        spec_order_id=spec_order_id,
        contract_id=contract_id,
        object_id=object_id,
        user_id=user_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        region_id=region_id,
        arial_id=arial_id,
        locality_id=locality_id,
        street_id=street_id,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages
    )

@router.get("/my", response_model=PaginatedResponse[OrderListResponse])
async def get_my_orders(
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список своих заявок с пагинацией
    
    Требуется право: order_read
    """
    items, total = await order_service.get_orders_by_current_user(
        pagination=pagination,
        current_user=current_user,
        status=status
    )
    
    # Формируем результат для списка
    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "number": item.number,
            "created_at": item.created_at,
            "status": item.status,
            "report_id": item.report_id,
            "spec_order_name": item.spec_order.name if item.spec_order else None,
            "object_name": item.object.name if item.object else None,
            "user_name": item.user.name if item.user else None,
            "contract_number": item.contract.number if item.contract else None
        })
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=result_items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages
    )

@router.get("/options", response_model=List[OrderOptionResponse])
async def get_order_options(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список заявок для выпадающих списков
    
    Требуется право: order_read
    """
    orders = await order_service.get_order_options(current_user, status=status)
    
    return [
        {
            "id": item.id,
            "number": item.number,
            "status": item.status
        }
        for item in orders
    ]

@router.get("/by-status/{status}", response_model=List[OrderListResponse])
async def get_orders_by_status(
    status: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить заявки по статусу
    
    Требуется право: order_read
    """
    items, _ = await order_service.get_orders_paginated_with_details(
        pagination=PaginationParams(page=1, per_page=100),
        current_user=current_user,
        status=status
    )
    
    return items

@router.post("/bulk-pdf")
async def bulk_order_pdf(
    payload: BulkPdfRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Сформировать ZIP-архив с PDF-актами по списку заявок.

    `kind='to'` — акт ТО (плановый), `kind='primary'` — акт первичного обследования,
    `kind='defect'` — акт дефектовки (диагностических и ремонтных работ).
    Требуется право: `order_read` (проверяется внутри render-функций).
    """
    render_by_kind = {
        "to": render_order_pdf,
        "primary": render_order_primary_pdf,
        "defect": render_order_defect_pdf,
    }
    if payload.kind not in render_by_kind:
        raise HTTPException(400, detail="kind должен быть 'to', 'primary' или 'defect'")

    render_fn = render_by_kind[payload.kind]

    buf = io.BytesIO()
    errors: list[str] = []
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for oid in payload.order_ids:
            try:
                pdf_bytes, filename = await render_fn(oid, current_user)
            except HTTPException as e:
                # 403 (нет прав) — останавливаем сразу, остальные пропускаем
                if e.status_code == 403:
                    raise
                errors.append(f"order_id={oid}: {e.detail}")
                continue
            except Exception as e:
                errors.append(f"order_id={oid}: {e}")
                continue
            zf.writestr(_safe_zip_name(filename), pdf_bytes)

        if errors:
            zf.writestr("_errors.txt", "\n".join(errors).encode("utf-8"))

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_name = f"acts_{payload.kind}_{ts}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{archive_name}"'},
    )


@router.get("/{order_id}/pdf")
async def get_order_pdf(
    order_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Сформировать PDF акта выполненных работ по заявке.

    Шаблон выбирается по типу заявки (`spec_order`).
    Сейчас поддерживается только «плановая».

    Требуется право: order_read
    """
    pdf_bytes, filename = await render_order_pdf(order_id, current_user)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{order_id}/primary/pdf")
async def get_order_primary_pdf(
    order_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Сформировать PDF акта первичного обследования по заявке.

    Дата акта оставляется пустой для ручного заполнения.

    Требуется право: order_read
    """
    pdf_bytes, filename = await render_order_primary_pdf(order_id, current_user)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{order_id}/defect/pdf")
async def get_order_defect_pdf(
    order_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Сформировать PDF акта дефектовки (диагностических и ремонтных работ) по заявке.

    Поля разделов и дата оставляются пустыми для ручного заполнения.

    Требуется право: order_read
    """
    pdf_bytes, filename = await render_order_defect_pdf(order_id, current_user)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{order_id}/render")
async def render_order_act(
    order_id: int,
    format: str = Query("docx", regex="^(docx|pdf)$", description="Формат документа: docx (стандарт) или pdf (требует LibreOffice на сервере)"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Сформировать заполненный акт по заявке на основе .docx/.dotx-шаблона,
    привязанного к её типу (spec_order.template_filename).

    Параллельно с устаревшими /pdf, /primary/pdf, /defect/pdf — те жёстко
    зашиты на HTML-шаблоны через WeasyPrint; новый /render работает по
    Word-шаблонам через docxtpl, что позволяет редактировать шаблоны
    в MS Word без участия разработчика.

    Список доступных placeholder'ов для шаблона смотри в разделе
    «Документация» приложения (Phase 3).

    Требуется право: order_read.
    """
    content, filename, media_type = await render_order_document(
        order_id, format, current_user
    )
    return Response(
        content=content,
        media_type=media_type,
        headers=build_attachment_headers(filename),
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить заявку по ID
    
    Требуется право: order_read
    """
    # Используем функцию с детальной информацией
    result = await order_service.get_order_with_details(
        order_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новую заявку
    
    user_id автоматически берется из текущего пользователя
    
    Требуется право: order_create
    """
    order = await order_service.create_order(
        order_data,
        current_user
    )
    
    # Возвращаем полную информацию
    return await order_service.get_order_with_details(order.id, current_user)

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить заявку
    
    Требуется право: order_modify
    """
    order = await order_service.update_order(
        order_id,
        order_data,
        current_user
    )
    
    # Возвращаем полную информацию
    return await order_service.get_order_with_details(order.id, current_user)

@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status: str = Query(..., description="Новый статус (new, in_progress, completed, cancelled)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить статус заявки
    
    Требуется право: order_modify
    """
    order = await order_service.update_order_status(
        order_id,
        status,
        current_user
    )
    
    # Возвращаем полную информацию
    return await order_service.get_order_with_details(order.id, current_user)

@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить заявку
    
    Требуется право: order_delete
    """
    await order_service.delete_order(
        order_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Заявка с id {order_id} успешно удалена"
    }