from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_room import (
    SpecRoomCreate,
    SpecRoomUpdate,
    SpecRoomResponse,
    SpecRoomListResponse,
    SpecRoomOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_room as spec_room_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_room", tags=["spec_room"])

@router.get("/list", response_model=PaginatedResponse[SpecRoomListResponse])
async def get_spec_room_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов помещений с пагинацией
    
    Требуется право: spec_room_read
    """
    items, total = await spec_room_service.get_spec_rooms_paginated_with_stats(
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

@router.get("/options", response_model=List[SpecRoomOptionResponse])
async def get_spec_room_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов помещений для выпадающих списков
    
    Требуется право: spec_room_read
    """
    spec_rooms = await spec_room_service.get_spec_room_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name
        }
        for item in spec_rooms
    ]

@router.get("/all", response_model=List[SpecRoomListResponse])
async def get_all_spec_rooms(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все типы помещений (без пагинации)
    
    Требуется право: spec_room_read
    """
    spec_rooms = await spec_room_service.get_all_spec_rooms(
        current_user,
        load_relations=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "organizations_count": len(item.organizations) if item.organizations else 0,
            "objects_count": len(item.objects) if item.objects else 0
        }
        for item in spec_rooms
    ]

@router.get("/{spec_room_id}", response_model=SpecRoomResponse)
async def get_spec_room_by_id(
    spec_room_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить тип помещения по ID
    
    Требуется право: spec_room_read
    """
    # Используем функцию со статистикой
    result = await spec_room_service.get_spec_room_with_stats(
        spec_room_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=SpecRoomResponse)
async def create_spec_room(
    spec_room_data: SpecRoomCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый тип помещения
    
    Требуется право: spec_room_create
    """
    spec_room = await spec_room_service.create_spec_room(
        spec_room_data,
        current_user
    )
    
    return {
        "id": spec_room.id,
        "name": spec_room.name,
        "organizations_count": 0,
        "objects_count": 0
    }

@router.put("/{spec_room_id}", response_model=SpecRoomResponse)
async def update_spec_room(
    spec_room_id: int,
    spec_room_data: SpecRoomUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить тип помещения
    
    Требуется право: spec_room_modify
    """
    spec_room = await spec_room_service.update_spec_room(
        spec_room_id,
        spec_room_data,
        current_user
    )
    
    # Получаем статистику для ответа
    async with spec_room_service.new_session() as session:
        organizations_count = await spec_room_service.spec_room_data.count_organizations(
            session, 
            spec_room_id
        )
        objects_count = await spec_room_service.spec_room_data.count_objects(
            session, 
            spec_room_id
        )
    
    return {
        "id": spec_room.id,
        "name": spec_room.name,
        "organizations_count": organizations_count,
        "objects_count": objects_count
    }

@router.delete("/{spec_room_id}")
async def delete_spec_room(
    spec_room_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить тип помещения
    
    Требуется право: spec_room_delete
    """
    await spec_room_service.delete_spec_room(
        spec_room_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Тип помещения с id {spec_room_id} успешно удален"
    }