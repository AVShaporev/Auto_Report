from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from model.user import User
from schema.spec_order_status import (
    SpecOrderStatusCreate,
    SpecOrderStatusUpdate,
    SpecOrderStatusResponse,
    SpecOrderStatusListResponse,
    SpecOrderStatusOptionResponse,
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_order_status as spec_order_status_service
from core.dependencies import get_current_active_user


router = APIRouter(prefix="/api/spec_order_status", tags=["spec_order_status"])


@router.get("/options", response_model=List[SpecOrderStatusOptionResponse])
async def get_options(
    current_user: User = Depends(get_current_active_user),
):
    """Все статусы для селектов. Публично внутри тенанта — только auth,
    без spec_order_status_read (иначе не создать заявку рядовому юзеру)."""
    rows = await spec_order_status_service.get_spec_order_status_options(current_user)
    return rows


@router.get("/list", response_model=PaginatedResponse[SpecOrderStatusListResponse])
async def get_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по имени/описанию"),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
):
    """Пагинированный список для админ-UI. Требует spec_order_status_read."""
    items, total = await spec_order_status_service.get_spec_order_status_paginated_with_stats(
        pagination=pagination,
        current_user=current_user,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    pages = (total + pagination.limit - 1) // pagination.limit
    return PaginatedResponse(
        items=items, total=total,
        page=pagination.page, per_page=pagination.limit, pages=pages,
    )


@router.get("/{spec_order_status_id}", response_model=SpecOrderStatusResponse)
async def get_by_id(
    spec_order_status_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Одна запись со счётчиком заявок. Требует spec_order_status_read."""
    return await spec_order_status_service.get_spec_order_status_with_stats(
        spec_order_status_id, current_user
    )


@router.post("/create", response_model=SpecOrderStatusResponse)
async def create(
    payload: SpecOrderStatusCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Создать. Требует spec_order_status_create."""
    return await spec_order_status_service.create_spec_order_status(payload, current_user)


@router.put("/{spec_order_status_id}", response_model=SpecOrderStatusResponse)
async def update(
    spec_order_status_id: int,
    payload: SpecOrderStatusUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Обновить. Требует spec_order_status_modify."""
    return await spec_order_status_service.update_spec_order_status(
        spec_order_status_id, payload, current_user
    )


@router.delete("/{spec_order_status_id}")
async def delete(
    spec_order_status_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Удалить. Требует spec_order_status_delete."""
    await spec_order_status_service.delete_spec_order_status(spec_order_status_id, current_user)
    return {"status": "success", "message": f"Статус с id {spec_order_status_id} удалён"}
