from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_street import (
    SpecStreetCreate,
    SpecStreetUpdate,
    SpecStreetResponse,
    SpecStreetListResponse,
    SpecStreetOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_street as spec_street_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_street", tags=["spec_street"])

@router.get("/list", response_model=PaginatedResponse[SpecStreetListResponse])
async def get_spec_street_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов улиц с пагинацией
    
    Требуется право: spec_street_read
    """
    items, total = await spec_street_service.get_spec_streets_paginated_with_stats(
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

@router.get("/options", response_model=List[SpecStreetOptionResponse])
async def get_spec_street_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов улиц для выпадающих списков
    
    Требуется право: spec_street_read
    """
    spec_streets = await spec_street_service.get_spec_street_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name
        }
        for item in spec_streets
    ]

@router.get("/all", response_model=List[SpecStreetListResponse])
async def get_all_spec_streets(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все типы улиц (без пагинации)
    
    Требуется право: spec_street_read
    """
    spec_streets = await spec_street_service.get_all_spec_streets(
        current_user,
        load_streets=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "streets_count": len(item.streets) if item.streets else 0
        }
        for item in spec_streets
    ]

@router.get("/{spec_street_id}", response_model=SpecStreetResponse)
async def get_spec_street_by_id(
    spec_street_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить тип улицы по ID
    
    Требуется право: spec_street_read
    """
    # Используем функцию со статистикой
    result = await spec_street_service.get_spec_street_with_stats(
        spec_street_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=SpecStreetResponse)
async def create_spec_street(
    spec_street_data: SpecStreetCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый тип улицы
    
    Требуется право: spec_street_create
    """
    spec_street = await spec_street_service.create_spec_street(
        spec_street_data,
        current_user
    )
    
    return {
        "id": spec_street.id,
        "name": spec_street.name,
        "streets_count": 0
    }

@router.put("/{spec_street_id}", response_model=SpecStreetResponse)
async def update_spec_street(
    spec_street_id: int,
    spec_street_data: SpecStreetUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить тип улицы
    
    Требуется право: spec_street_modify
    """
    spec_street = await spec_street_service.update_spec_street(
        spec_street_id,
        spec_street_data,
        current_user
    )
    
    # Получаем количество связанных улиц для ответа
    async with spec_street_service.new_session() as session:
        streets_count = await spec_street_service.spec_street_data.count_streets(
            session, 
            spec_street_id
        )
    
    return {
        "id": spec_street.id,
        "name": spec_street.name,
        "streets_count": streets_count
    }

@router.delete("/{spec_street_id}")
async def delete_spec_street(
    spec_street_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить тип улицы
    
    Требуется право: spec_street_delete
    """
    await spec_street_service.delete_spec_street(
        spec_street_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Тип улицы с id {spec_street_id} успешно удален"
    }