from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_order import (
    SpecOrderCreate,
    SpecOrderUpdate,
    SpecOrderResponse,
    SpecOrderListResponse,
    SpecOrderOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_order as spec_order_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_order", tags=["spec_order"])

@router.get("/list", response_model=PaginatedResponse[SpecOrderListResponse])
async def get_spec_order_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию или краткому наименованию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов заявок с пагинацией
    
    Требуется право: spec_order_read
    """
    items, total = await spec_order_service.get_spec_orders_paginated_with_stats(
        pagination=pagination,
        current_user=current_user,
        search=search,
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

@router.get("/options", response_model=List[SpecOrderOptionResponse])
async def get_spec_order_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов заявок для выпадающих списков
    
    Требуется право: spec_order_read
    """
    spec_orders = await spec_order_service.get_spec_order_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "short_name": item.short_name
        }
        for item in spec_orders
    ]

@router.get("/all", response_model=List[SpecOrderListResponse])
async def get_all_spec_orders(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все типы заявок (без пагинации)
    
    Требуется право: spec_order_read
    """
    spec_orders = await spec_order_service.get_all_spec_orders(
        current_user,
        load_orders=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "short_name": item.short_name,
            "orders_count": len(item.orders) if item.orders else 0
        }
        for item in spec_orders
    ]

@router.get("/{spec_order_id}", response_model=SpecOrderResponse)
async def get_spec_order_by_id(
    spec_order_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить тип заявки по ID
    
    Требуется право: spec_order_read
    """
    # Используем функцию со статистикой
    result = await spec_order_service.get_spec_order_with_stats(
        spec_order_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=SpecOrderResponse)
async def create_spec_order(
    spec_order_data: SpecOrderCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый тип заявки
    
    Требуется право: spec_order_create
    """
    spec_order = await spec_order_service.create_spec_order(
        spec_order_data,
        current_user
    )
    
    return {
        "id": spec_order.id,
        "name": spec_order.name,
        "short_name": spec_order.short_name,
        "orders_count": 0
    }

@router.put("/{spec_order_id}", response_model=SpecOrderResponse)
async def update_spec_order(
    spec_order_id: int,
    spec_order_data: SpecOrderUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить тип заявки
    
    Требуется право: spec_order_modify
    """
    return await spec_order_service.update_spec_order_with_stats(
        spec_order_id,
        spec_order_data,
        current_user
    )

@router.delete("/{spec_order_id}")
async def delete_spec_order(
    spec_order_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить тип заявки
    
    Требуется право: spec_order_delete
    """
    await spec_order_service.delete_spec_order(
        spec_order_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Тип заявки с id {spec_order_id} успешно удален"
    }