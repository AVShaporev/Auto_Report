from fastapi import APIRouter, Depends, Query, HTTPException
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
from core.dependencies import get_current_active_user

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