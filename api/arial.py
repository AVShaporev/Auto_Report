from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.arial import (
    ArialCreate,
    ArialUpdate,
    ArialResponse,
    ArialListResponse,
    ArialOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import arial as arial_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/arial", tags=["arial"])

@router.get("/list", response_model=PaginatedResponse[ArialListResponse])
async def get_arial_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    spec_arial_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу района"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список районов с пагинацией
    
    Требуется право: arial_read
    """
    items, total = await arial_service.get_arials_paginated_with_stats(
        pagination=pagination,
        current_user=current_user,
        search=search,
        spec_arial_id=spec_arial_id,
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

@router.get("/options", response_model=List[ArialOptionResponse])
async def get_arial_options(
    spec_arial_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу района"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список районов для выпадающих списков
    
    Требуется право: arial_read
    """
    if spec_arial_id:
        # Получаем районы по типу
        arials = await arial_service.get_arial_options_by_spec(spec_arial_id, current_user)
    else:
        # Получаем все районы
        arials = await arial_service.get_arial_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name
        }
        for item in arials
    ]

@router.get("/all", response_model=List[ArialListResponse])
async def get_all_arials(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все районы (без пагинации)
    
    Требуется право: arial_read
    """
    arials = await arial_service.get_all_arials(
        current_user,
        load_relations=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "spec_arial_name": item.spec_arial.name if item.spec_arial else None,
            "organizations_count": len(item.organizations) if item.organizations else 0,
            "objects_count": len(item.objects) if item.objects else 0
        }
        for item in arials
    ]

@router.get("/{arial_id}", response_model=ArialResponse)
async def get_arial_by_id(
    arial_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить район по ID
    
    Требуется право: arial_read
    """
    # Используем функцию со статистикой
    result = await arial_service.get_arial_with_stats(
        arial_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=ArialResponse)
async def create_arial(
    arial_data: ArialCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый район
    
    Требуется право: arial_create
    """
    arial = await arial_service.create_arial(
        arial_data,
        current_user
    )
    
    return {
        "id": arial.id,
        "name": arial.name,
        "spec_arial_id": arial.spec_arial_id,
        "spec_arial_name": None,  # Будет подгружено при следующем запросе
        "organizations_count": 0,
        "objects_count": 0
    }

@router.put("/{arial_id}", response_model=ArialResponse)
async def update_arial(
    arial_id: int,
    arial_data: ArialUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить район
    
    Требуется право: arial_modify
    """
    arial = await arial_service.update_arial(
        arial_id,
        arial_data,
        current_user
    )
    
    # Получаем статистику для ответа
    async with arial_service.new_session() as session:
        organizations_count = await arial_service.arial_data.count_organizations(
            session, 
            arial_id
        )
        objects_count = await arial_service.arial_data.count_objects(
            session, 
            arial_id
        )
    
    return {
        "id": arial.id,
        "name": arial.name,
        "spec_arial_id": arial.spec_arial_id,
        "spec_arial_name": None,  # Будет подгружено при следующем запросе
        "organizations_count": organizations_count,
        "objects_count": objects_count
    }

@router.delete("/{arial_id}")
async def delete_arial(
    arial_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить район
    
    Требуется право: arial_delete
    """
    await arial_service.delete_arial(
        arial_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Район с id {arial_id} успешно удален"
    }