from fastapi import APIRouter, Depends, Query
from typing import Optional, List

from model.user import User
from schema.spec_status import (
    SpecStatusCreate,
    SpecStatusUpdate,
    SpecStatusResponse,
    SpecStatusListResponse,
    SpecStatusOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_status as spec_status_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_status", tags=["spec_status"])

@router.get("/list", response_model=PaginatedResponse[SpecStatusListResponse])
async def get_spec_status_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по наименованию или коду"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """Получить список статусов с пагинацией. Требуется право: spec_status_read"""
    items, total = await spec_status_service.get_spec_statuses_paginated_with_stats(
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

@router.get("/options", response_model=List[SpecStatusOptionResponse])
async def get_spec_status_options(
    current_user: User = Depends(get_current_active_user)
):
    """Получить список статусов для выпадающих списков. Требуется право: spec_status_read"""
    spec_statuses = await spec_status_service.get_spec_status_options(current_user)

    return [
        {
            "id": item.id,
            "name": item.name,
            "code": item.code
        }
        for item in spec_statuses
    ]

@router.get("/all", response_model=List[SpecStatusListResponse])
async def get_all_spec_statuses(
    current_user: User = Depends(get_current_active_user)
):
    """Получить все статусы (без пагинации). Требуется право: spec_status_read"""
    spec_statuses = await spec_status_service.get_all_spec_statuses(
        current_user,
        load_issues=True
    )

    return [
        {
            "id": item.id,
            "name": item.name,
            "code": item.code,
            "issues_count": len(item.issues) if item.issues else 0
        }
        for item in spec_statuses
    ]

@router.get("/{spec_status_id}", response_model=SpecStatusResponse)
async def get_spec_status_by_id(
    spec_status_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Получить статус по ID. Требуется право: spec_status_read"""
    return await spec_status_service.get_spec_status_with_stats(
        spec_status_id,
        current_user
    )

@router.post("/create", response_model=SpecStatusResponse)
async def create_spec_status(
    spec_status_data: SpecStatusCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Создать новый статус. Требуется право: spec_status_create"""
    spec_status = await spec_status_service.create_spec_status(
        spec_status_data,
        current_user
    )

    return {
        "id": spec_status.id,
        "name": spec_status.name,
        "code": spec_status.code,
        "issues_count": 0
    }

@router.put("/{spec_status_id}", response_model=SpecStatusResponse)
async def update_spec_status(
    spec_status_id: int,
    spec_status_data: SpecStatusUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Обновить статус. Требуется право: spec_status_modify"""
    return await spec_status_service.update_spec_status_with_stats(
        spec_status_id,
        spec_status_data,
        current_user
    )

@router.delete("/{spec_status_id}")
async def delete_spec_status(
    spec_status_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Удалить статус. Требуется право: spec_status_delete"""
    await spec_status_service.delete_spec_status(
        spec_status_id,
        current_user
    )

    return {
        "status": "success",
        "message": f"Статус с id {spec_status_id} успешно удален"
    }
