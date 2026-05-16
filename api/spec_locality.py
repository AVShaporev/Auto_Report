from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_locality import (
    SpecLocalityCreate,
    SpecLocalityUpdate,
    SpecLocalityResponse,
    SpecLocalityListResponse,
    SpecLocalityOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_locality as spec_locality_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_locality", tags=["spec_locality"])

@router.get("/list", response_model=PaginatedResponse[SpecLocalityListResponse])
async def get_spec_locality_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов населенных пунктов с пагинацией
    
    Требуется право: spec_locality_read
    """
    items, total = await spec_locality_service.get_spec_localities_paginated_with_stats(
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

@router.get("/options", response_model=List[SpecLocalityOptionResponse])
async def get_spec_locality_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов населенных пунктов для выпадающих списков
    
    Требуется право: spec_locality_read
    """
    spec_localities = await spec_locality_service.get_spec_locality_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "short_name": item.short_name
        }
        for item in spec_localities
    ]

@router.get("/all", response_model=List[SpecLocalityListResponse])
async def get_all_spec_localities(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все типы населенных пунктов (без пагинации)
    
    Требуется право: spec_locality_read
    """
    spec_localities = await spec_locality_service.get_all_spec_localities(
        current_user,
        load_localities=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "short_name": item.short_name,
            "localities_count": len(item.localitys) if item.localitys else 0
        }
        for item in spec_localities
    ]

@router.get("/{spec_locality_id}", response_model=SpecLocalityResponse)
async def get_spec_locality_by_id(
    spec_locality_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить тип населенного пункта по ID
    
    Требуется право: spec_locality_read
    """
    # Используем функцию со статистикой
    result = await spec_locality_service.get_spec_locality_with_stats(
        spec_locality_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=SpecLocalityResponse)
async def create_spec_locality(
    spec_locality_data: SpecLocalityCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый тип населенного пункта
    
    Требуется право: spec_locality_create
    """
    spec_locality = await spec_locality_service.create_spec_locality(
        spec_locality_data,
        current_user
    )
    
    return {
        "id": spec_locality.id,
        "name": spec_locality.name,
        "short_name": spec_locality.short_name,
        "localities_count": 0
    }

@router.put("/{spec_locality_id}", response_model=SpecLocalityResponse)
async def update_spec_locality(
    spec_locality_id: int,
    spec_locality_data: SpecLocalityUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить тип населенного пункта
    
    Требуется право: spec_locality_modify
    """
    spec_locality = await spec_locality_service.update_spec_locality(
        spec_locality_id,
        spec_locality_data,
        current_user
    )
    
    # Получаем количество связанных населенных пунктов для ответа
    async with spec_locality_service.new_session() as session:
        localities_count = await spec_locality_service.spec_locality_data.count_localities_by_spec_locality(
            session, 
            spec_locality_id
        )
    
    return {
        "id": spec_locality.id,
        "name": spec_locality.name,
        "short_name": spec_locality.short_name,
        "localities_count": localities_count
    }

@router.delete("/{spec_locality_id}")
async def delete_spec_locality(
    spec_locality_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить тип населенного пункта
    
    Требуется право: spec_locality_delete
    """
    await spec_locality_service.delete_spec_locality(
        spec_locality_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Тип населенного пункта с id {spec_locality_id} успешно удален"
    }