from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.street import (
    StreetCreate,
    StreetUpdate,
    StreetResponse,
    StreetListResponse,
    StreetOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import street as street_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/street", tags=["street"])

@router.get("/list", response_model=PaginatedResponse[StreetListResponse])
async def get_street_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    spec_street_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу улицы"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список улиц с пагинацией
    
    Требуется право: street_read
    """
    items, total = await street_service.get_streets_paginated_with_stats(
        pagination=pagination,
        current_user=current_user,
        search=search,
        spec_street_id=spec_street_id,
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

@router.get("/options", response_model=List[StreetOptionResponse])
async def get_street_options(
    spec_street_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу улицы"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список улиц для выпадающих списков
    
    Требуется право: street_read
    """
    if spec_street_id:
        # Получаем улицы по типу
        streets = await street_service.get_street_options_by_spec(spec_street_id, current_user)
    else:
        # Получаем все улицы
        streets = await street_service.get_street_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name
        }
        for item in streets
    ]

@router.get("/all", response_model=List[StreetListResponse])
async def get_all_streets(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все улицы (без пагинации)
    
    Требуется право: street_read
    """
    streets = await street_service.get_all_streets(
        current_user,
        load_relations=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "spec_street_name": item.spec_street.name if item.spec_street else None,
            "organizations_count": len(item.organizations) if item.organizations else 0,
            "objects_count": len(item.objects) if item.objects else 0
        }
        for item in streets
    ]

@router.get("/{street_id}", response_model=StreetResponse)
async def get_street_by_id(
    street_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить улицу по ID
    
    Требуется право: street_read
    """
    # Используем функцию со статистикой
    result = await street_service.get_street_with_stats(
        street_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=StreetResponse)
async def create_street(
    street_data: StreetCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новую улицу
    
    Требуется право: street_create
    """
    street = await street_service.create_street(
        street_data,
        current_user
    )
    
    return {
        "id": street.id,
        "name": street.name,
        "spec_street_id": street.spec_street_id,
        "spec_street_name": None,
        "organizations_count": 0,
        "objects_count": 0
    }

@router.put("/{street_id}", response_model=StreetResponse)
async def update_street(
    street_id: int,
    street_data: StreetUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить улицу
    
    Требуется право: street_modify
    """
    street = await street_service.update_street(
        street_id,
        street_data,
        current_user
    )
    
    # Получаем статистику для ответа
    async with street_service.new_session() as session:
        organizations_count = await street_service.street_data.count_organizations(
            session, 
            street_id
        )
        objects_count = await street_service.street_data.count_objects(
            session, 
            street_id
        )
    
    return {
        "id": street.id,
        "name": street.name,
        "spec_street_id": street.spec_street_id,
        "spec_street_name": None,
        "organizations_count": organizations_count,
        "objects_count": objects_count
    }

@router.delete("/{street_id}")
async def delete_street(
    street_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить улицу
    
    Требуется право: street_delete
    """
    await street_service.delete_street(
        street_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Улица с id {street_id} успешно удалена"
    }