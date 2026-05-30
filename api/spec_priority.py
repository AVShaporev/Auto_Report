from fastapi import APIRouter, Depends, Query
from typing import Optional, List

from model.user import User
from schema.spec_priority import (
    SpecPriorityCreate,
    SpecPriorityUpdate,
    SpecPriorityResponse,
    SpecPriorityListResponse,
    SpecPriorityOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_priority as spec_priority_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_priority", tags=["spec_priority"])


@router.get("/list", response_model=PaginatedResponse[SpecPriorityListResponse])
async def get_spec_priority_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по наименованию или коду"),
    sort_by: str = Query("id", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """Список приоритетов с пагинацией. Требуется право: spec_priority_read"""
    items, total = await spec_priority_service.get_spec_priorities_paginated_with_stats(
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


@router.get("/options", response_model=List[SpecPriorityOptionResponse])
async def get_spec_priority_options(
    current_user: User = Depends(get_current_active_user)
):
    """Приоритеты для выпадающих списков. Требуется право: spec_priority_read"""
    items = await spec_priority_service.get_spec_priority_options(current_user)
    return [{"id": i.id, "name": i.name, "code": i.code} for i in items]


@router.get("/all", response_model=List[SpecPriorityListResponse])
async def get_all_spec_priorities(
    current_user: User = Depends(get_current_active_user)
):
    """Все приоритеты (без пагинации). Требуется право: spec_priority_read"""
    items = await spec_priority_service.get_all_spec_priorities(current_user, load_issues=True)
    return [
        {
            "id": i.id,
            "name": i.name,
            "code": i.code,
            "description": i.description,
            "issues_count": len(i.issues) if i.issues else 0
        }
        for i in items
    ]


@router.get("/{spec_priority_id}", response_model=SpecPriorityResponse)
async def get_spec_priority_by_id(
    spec_priority_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Приоритет по ID. Требуется право: spec_priority_read"""
    return await spec_priority_service.get_spec_priority_with_stats(
        spec_priority_id,
        current_user
    )


@router.post("/create", response_model=SpecPriorityResponse)
async def create_spec_priority(
    spec_priority_data: SpecPriorityCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Создать приоритет. Требуется право: spec_priority_create"""
    spec_priority = await spec_priority_service.create_spec_priority(
        spec_priority_data,
        current_user
    )
    return {
        "id": spec_priority.id,
        "name": spec_priority.name,
        "code": spec_priority.code,
        "description": spec_priority.description,
        "issues_count": 0
    }


@router.put("/{spec_priority_id}", response_model=SpecPriorityResponse)
async def update_spec_priority(
    spec_priority_id: int,
    spec_priority_data: SpecPriorityUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Обновить приоритет. Требуется право: spec_priority_modify"""
    return await spec_priority_service.update_spec_priority_with_stats(
        spec_priority_id,
        spec_priority_data,
        current_user
    )


@router.delete("/{spec_priority_id}")
async def delete_spec_priority(
    spec_priority_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Удалить приоритет. Требуется право: spec_priority_delete"""
    await spec_priority_service.delete_spec_priority(spec_priority_id, current_user)
    return {
        "status": "success",
        "message": f"Приоритет с id {spec_priority_id} успешно удален"
    }
