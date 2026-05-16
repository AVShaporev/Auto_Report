from fastapi import APIRouter, Depends, Query
from typing import Optional, List

from model.user import User
from schema.operation import (
    OperationCreate,
    OperationUpdate,
    OperationResponse,
    OperationListResponse,
    OperationOptionResponse,
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import operation as operation_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/operation", tags=["operation"])


@router.get("/list", response_model=PaginatedResponse[OperationListResponse])
async def get_operation_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по name/short_name/description"),
    spec_equipment_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу оборудования"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить список операций с пагинацией.
    Требуется право: operation_read
    """
    items, total = await operation_service.get_operations_paginated_with_details(
        pagination=pagination,
        current_user=current_user,
        search=search,
        spec_equipment_id=spec_equipment_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    pages = (total + pagination.limit - 1) // pagination.limit
    return PaginatedResponse(
        items=items, total=total,
        page=pagination.page, per_page=pagination.limit, pages=pages,
    )


@router.get("/all", response_model=List[OperationListResponse])
async def get_all_operations(
    current_user: User = Depends(get_current_active_user),
):
    """Все операции без пагинации. Право: operation_read"""
    return await operation_service.get_all_operations(current_user)


@router.get("/options", response_model=List[OperationOptionResponse])
async def get_operation_options(
    spec_equipment_id: Optional[int] = Query(None, ge=1),
    current_user: User = Depends(get_current_active_user),
):
    """Операции для выпадающих списков (опционально фильтр по типу оборудования). Право: operation_read"""
    return await operation_service.get_operation_options(current_user, spec_equipment_id)


@router.get("/{operation_id}", response_model=OperationResponse)
async def get_operation_by_id(
    operation_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Получить операцию по ID. Право: operation_read"""
    return await operation_service.get_operation_with_details(operation_id, current_user)


@router.post("/create", response_model=OperationResponse)
async def create_operation(
    payload: OperationCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Создать операцию. Право: operation_create"""
    return await operation_service.create_operation(payload, current_user)


@router.put("/{operation_id}", response_model=OperationResponse)
async def update_operation(
    operation_id: int,
    payload: OperationUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Обновить операцию (если передан spec_equipment_ids — полностью заменяет список). Право: operation_modify"""
    return await operation_service.update_operation(operation_id, payload, current_user)


@router.delete("/{operation_id}")
async def delete_operation(
    operation_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Удалить операцию. Право: operation_delete"""
    await operation_service.delete_operation(operation_id, current_user)
    return {"status": "success", "message": f"Операция с id {operation_id} удалена"}
