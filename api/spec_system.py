from fastapi import APIRouter, Depends, Query
from typing import Optional, List

from model.user import User
from schema.spec_system import (
    SpecSystemCreate,
    SpecSystemUpdate,
    SpecSystemResponse,
    SpecSystemListResponse,
    SpecSystemOptionResponse,
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_system as spec_system_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_system", tags=["spec_system"])


@router.get("/list", response_model=PaginatedResponse[SpecSystemListResponse])
async def get_spec_system_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    is_fire_protection: Optional[bool] = Query(None, description="Фильтр по принадлежности к ПЗ"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить список типов обслуживаемых систем с пагинацией

    Требуется право: spec_system_read
    """
    items, total = await spec_system_service.get_spec_systems_paginated_with_stats(
        pagination=pagination,
        current_user=current_user,
        search=search,
        is_fire_protection=is_fire_protection,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    pages = (total + pagination.limit - 1) // pagination.limit

    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages,
    )


@router.get("/options", response_model=List[SpecSystemOptionResponse])
async def get_spec_system_options(
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить минимальный список типов обслуживаемых систем для выпадающих списков

    Требуется право: spec_system_read
    """
    items = await spec_system_service.get_spec_system_options(current_user)
    return [
        {
            "id": item.id,
            "name": item.name,
            "short_name": item.short_name,
            "is_fire_protection": item.is_fire_protection,
        }
        for item in items
    ]


@router.get("/all", response_model=List[SpecSystemListResponse])
async def get_all_spec_systems(
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить все типы обслуживаемых систем (без пагинации)

    Требуется право: spec_system_read
    """
    return await spec_system_service.get_all_spec_systems(current_user)


@router.get("/{spec_system_id}", response_model=SpecSystemResponse)
async def get_spec_system_by_id(
    spec_system_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить тип обслуживаемой системы по ID

    Требуется право: spec_system_read
    """
    return await spec_system_service.get_spec_system_with_stats(spec_system_id, current_user)


@router.post("/create", response_model=SpecSystemResponse)
async def create_spec_system(
    payload: SpecSystemCreate,
    current_user: User = Depends(get_current_active_user),
):
    """
    Создать новый тип обслуживаемой системы

    Требуется право: spec_system_create
    """
    return await spec_system_service.create_spec_system(payload, current_user)


@router.put("/{spec_system_id}", response_model=SpecSystemResponse)
async def update_spec_system(
    spec_system_id: int,
    payload: SpecSystemUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """
    Обновить тип обслуживаемой системы

    Требуется право: spec_system_modify
    """
    return await spec_system_service.update_spec_system_with_stats(
        spec_system_id, payload, current_user,
    )


@router.delete("/{spec_system_id}")
async def delete_spec_system(
    spec_system_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Удалить тип обслуживаемой системы

    Требуется право: spec_system_delete
    """
    await spec_system_service.delete_spec_system(spec_system_id, current_user)
    return {
        "status": "success",
        "message": f"Тип обслуживаемой системы с id {spec_system_id} успешно удалён",
    }
