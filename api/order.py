from fastapi import APIRouter, Depends, Query, Response
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
from service.render_docx import render_order_document, render_orders_bulk_zip, build_attachment_headers
from core.dependencies import get_current_active_user


class BulkRenderRequest(BaseModel):
    """Тело запроса для массового рендера актов через docxtpl."""
    order_ids: List[int] = Field(..., min_length=1, max_length=100,
                                  description="ID заявок (1..100 за раз)")
    format: str = Field("docx", pattern="^(docx|pdf)$",
                        description="Формат: 'docx' (быстро) или 'pdf' (медленнее, soffice)")


class BulkAssignRequest(BaseModel):
    """Тело запроса для массового назначения ответственного."""
    order_ids: List[int] = Field(..., min_length=1, max_length=500,
                                  description="ID заявок (1..500 за раз)")
    assigned_to_id: Optional[int] = Field(
        None, ge=0,
        description="ID нового ответственного; null или 0 → снять ответственного",
    )


router = APIRouter(prefix="/api/order", tags=["order"])

@router.get("/list", response_model=PaginatedResponse[OrderListResponse])
async def get_order_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по номеру или описанию"),
    spec_order_id: Optional[List[int]] = Query(None, description="Фильтр по типам заявки (можно несколько)"),
    contract_id: Optional[int] = Query(None, ge=1, description="Фильтр по контракту"),
    object_id: Optional[int] = Query(None, ge=1, description="Фильтр по объекту"),
    user_id: Optional[int] = Query(None, ge=1, description="Фильтр по автору"),
    assigned_to_id: Optional[int] = Query(None, ge=0, description="Фильтр по ответственному; 0 = без ответственного"),
    status_id: Optional[List[int]] = Query(None, description="Фильтр по статусам (мультиселект spec_order_statuses.id)"),
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
        assigned_to_id=assigned_to_id,
        status_id=status_id,
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
    status_id: Optional[List[int]] = Query(None, description="Фильтр по статусам (мультиселект)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список своих заявок с пагинацией

    Требуется право: order_read
    """
    items, total = await order_service.get_orders_by_current_user(
        pagination=pagination,
        current_user=current_user,
        status_id=status_id
    )

    # Формируем результат для списка
    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "number": item.number,
            "created_at": item.created_at,
            "status_id": item.status_id,
            "status_name": item.spec_order_status.name if item.spec_order_status else None,
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
    status_id: Optional[int] = Query(None, ge=1, description="Фильтр по статусу"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список заявок для выпадающих списков

    Требуется право: order_read
    """
    orders = await order_service.get_order_options(current_user, status_id=status_id)

    return [
        {
            "id": item.id,
            "number": item.number,
            "status_id": item.status_id,
            "status_name": item.spec_order_status.name if item.spec_order_status else None,
        }
        for item in orders
    ]

@router.get("/by-status/{status_id}", response_model=List[OrderListResponse])
async def get_orders_by_status(
    status_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить заявки по статусу (spec_order_statuses.id)

    Требуется право: order_read
    """
    items, _ = await order_service.get_orders_paginated_with_details(
        pagination=PaginationParams(page=1, per_page=100),
        current_user=current_user,
        status_id=[status_id]
    )

    return items

@router.post("/bulk_assign")
async def bulk_assign_responsible(
    payload: BulkAssignRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Массово проставить (или снять) ответственного у списка заявок.

    Body: `{order_ids: [1,2,3], assigned_to_id: 42}` или
          `{order_ids: [1,2,3], assigned_to_id: null}` (снять).

    Требуется право: order_modify. Кандидатов на роль ответственного
    фронт выбирает сам (без админов/суперадминов) — бэк принимает любого
    существующего юзера.

    Возвращает `{updated: <int>}` — сколько заявок реально изменено.
    """
    updated = await order_service.bulk_assign_responsible(
        order_ids=payload.order_ids,
        assigned_to_id=payload.assigned_to_id,
        current_user=current_user,
    )
    return {"updated": updated}


@router.post("/render_zip")
async def render_orders_zip(
    payload: BulkRenderRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Массовое скачивание актов по нескольким заявкам в одном ZIP.

    Каждая заявка рендерится по своему шаблону (spec_order.template_storage_path).
    Если одна провалилась — пропускаем, остальные собираются в архив;
    в ZIP добавляется errors.txt со списком ошибок.

    Для PDF-формата каждая заявка дополнительно конвертируется через soffice
    headless (медленно, ~3-5s на акт). 100 PDF-актов ≈ 5-8 минут.

    Требуется право: order_read (проверяется на каждую заявку отдельно).
    """
    content, filename, media_type = await render_orders_bulk_zip(
        payload.order_ids, payload.format, current_user
    )
    return Response(
        content=content,
        media_type=media_type,
        headers=build_attachment_headers(filename),
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
    status_id: int = Query(..., ge=1, description="ID нового статуса (spec_order_statuses.id)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить статус заявки. Валидация — FK constraint на DB.

    Требуется право: order_modify
    """
    order = await order_service.update_order_status(
        order_id,
        status_id,
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