from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_arial import (
    SpecArialCreate,
    SpecArialUpdate,
    SpecArialResponse,
    SpecArialListResponse,
    SpecArialOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_arial as spec_arial_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_arial", tags=["spec_arial"])

@router.get("/list", response_model=PaginatedResponse[SpecArialListResponse])
async def get_spec_arial_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов районов с пагинацией
    
    Требуется право: spec_arial_read
    """
    items, total = await spec_arial_service.get_spec_arials_paginated_with_stats(
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

@router.get("/options", response_model=List[SpecArialOptionResponse])
async def get_spec_arial_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов районов для выпадающих списков
    
    Требуется право: spec_arial_read
    """
    spec_arials = await spec_arial_service.get_spec_arial_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name
        }
        for item in spec_arials
    ]

@router.get("/all", response_model=List[SpecArialListResponse])
async def get_all_spec_arials(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все типы районов (без пагинации)
    
    Требуется право: spec_arial_read
    """
    spec_arials = await spec_arial_service.get_all_spec_arials(
        current_user,
        load_arials=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "arials_count": len(item.arials) if item.arials else 0
        }
        for item in spec_arials
    ]

@router.get("/{spec_arial_id}", response_model=SpecArialResponse)
async def get_spec_arial_by_id(
    spec_arial_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить тип района по ID
    
    Требуется право: spec_arial_read
    """
    # Используем функцию со статистикой
    result = await spec_arial_service.get_spec_arial_with_stats(
        spec_arial_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=SpecArialResponse)
async def create_spec_arial(
    spec_arial_data: SpecArialCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый тип района
    
    Требуется право: spec_arial_create
    """
    spec_arial = await spec_arial_service.create_spec_arial(
        spec_arial_data,
        current_user
    )
    
    return {
        "id": spec_arial.id,
        "name": spec_arial.name,
        "arials_count": 0
    }

@router.put("/{spec_arial_id}", response_model=SpecArialResponse)
async def update_spec_arial(
    spec_arial_id: int,
    spec_arial_data: SpecArialUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить тип района
    
    Требуется право: spec_arial_modify
    """
    spec_arial = await spec_arial_service.update_spec_arial(
        spec_arial_id,
        spec_arial_data,
        current_user
    )
    
    # Получаем количество связанных районов для ответа
    async with spec_arial_service.new_session() as session:
        arials_count = await spec_arial_service.spec_arial_data.count_arials(
            session, 
            spec_arial_id
        )
    
    return {
        "id": spec_arial.id,
        "name": spec_arial.name,
        "arials_count": arials_count
    }

@router.delete("/{spec_arial_id}")
async def delete_spec_arial(
    spec_arial_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить тип района
    
    Требуется право: spec_arial_delete
    """
    await spec_arial_service.delete_spec_arial(
        spec_arial_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Тип района с id {spec_arial_id} успешно удален"
    }