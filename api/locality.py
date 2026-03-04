from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.locality import (
    LocalityCreate,
    LocalityUpdate,
    LocalityResponse,
    LocalityListResponse,
    LocalityOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import locality as locality_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/locality", tags=["locality"])

@router.get("/list", response_model=PaginatedResponse[LocalityListResponse])
async def get_locality_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    spec_locality_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу населенного пункта"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список населенных пунктов с пагинацией
    
    Требуется право: locality_read
    """
    items, total = await locality_service.get_localities_paginated_with_stats(
        pagination=pagination,
        current_user=current_user,
        search=search,
        spec_locality_id=spec_locality_id,
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

@router.get("/options", response_model=List[LocalityOptionResponse])
async def get_locality_options(
    spec_locality_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу населенного пункта"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список населенных пунктов для выпадающих списков
    
    Требуется право: locality_read
    """
    if spec_locality_id:
        # Получаем населенные пункты по типу
        localities = await locality_service.get_locality_options_by_spec(spec_locality_id, current_user)
    else:
        # Получаем все населенные пункты
        localities = await locality_service.get_locality_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name
        }
        for item in localities
    ]

@router.get("/all", response_model=List[LocalityListResponse])
async def get_all_localities(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все населенные пункты (без пагинации)
    
    Требуется право: locality_read
    """
    localities = await locality_service.get_all_localities(
        current_user,
        load_relations=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "spec_locality_name": item.spec_locality.name if item.spec_locality else None,
            "organizations_count": len(item.organizations) if item.organizations else 0,
            "objects_count": len(item.objects) if item.objects else 0
        }
        for item in localities
    ]

@router.get("/{locality_id}", response_model=LocalityResponse)
async def get_locality_by_id(
    locality_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить населенный пункт по ID
    
    Требуется право: locality_read
    """
    # Используем функцию со статистикой
    result = await locality_service.get_locality_with_stats(
        locality_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=LocalityResponse)
async def create_locality(
    locality_data: LocalityCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый населенный пункт
    
    Требуется право: locality_create
    """
    locality = await locality_service.create_locality(
        locality_data,
        current_user
    )
    
    return {
        "id": locality.id,
        "name": locality.name,
        "spec_locality_id": locality.spec_locality_id,
        "spec_locality_name": None,
        "spec_locality_short_name": None,
        "organizations_count": 0,
        "objects_count": 0
    }

@router.put("/{locality_id}", response_model=LocalityResponse)
async def update_locality(
    locality_id: int,
    locality_data: LocalityUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить населенный пункт
    
    Требуется право: locality_modify
    """
    locality = await locality_service.update_locality(
        locality_id,
        locality_data,
        current_user
    )
    
    # Получаем статистику для ответа
    async with locality_service.new_session() as session:
        organizations_count = await locality_service.locality_data.count_organizations(
            session, 
            locality_id
        )
        objects_count = await locality_service.locality_data.count_objects(
            session, 
            locality_id
        )
    
    return {
        "id": locality.id,
        "name": locality.name,
        "spec_locality_id": locality.spec_locality_id,
        "spec_locality_name": None,
        "spec_locality_short_name": None,
        "organizations_count": organizations_count,
        "objects_count": objects_count
    }

@router.delete("/{locality_id}")
async def delete_locality(
    locality_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить населенный пункт
    
    Требуется право: locality_delete
    """
    await locality_service.delete_locality(
        locality_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Населенный пункт с id {locality_id} успешно удален"
    }