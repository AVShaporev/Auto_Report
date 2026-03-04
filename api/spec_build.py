from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_build import (
    SpecBuildCreate,
    SpecBuildUpdate,
    SpecBuildResponse,
    SpecBuildListResponse,
    SpecBuildOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_build as spec_build_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_build", tags=["spec_build"])

@router.get("/list", response_model=PaginatedResponse[SpecBuildListResponse])
async def get_spec_build_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов строений с пагинацией
    
    Требуется право: spec_build_read
    """
    items, total = await spec_build_service.get_spec_builds_paginated_with_stats(
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

@router.get("/options", response_model=List[SpecBuildOptionResponse])
async def get_spec_build_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов строений для выпадающих списков
    
    Требуется право: spec_build_read
    """
    spec_builds = await spec_build_service.get_spec_build_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name
        }
        for item in spec_builds
    ]

@router.get("/all", response_model=List[SpecBuildListResponse])
async def get_all_spec_builds(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все типы строений (без пагинации)
    
    Требуется право: spec_build_read
    """
    spec_builds = await spec_build_service.get_all_spec_builds(
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
        for item in spec_builds
    ]

@router.get("/{spec_build_id}", response_model=SpecBuildResponse)
async def get_spec_build_by_id(
    spec_build_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить тип строения по ID
    
    Требуется право: spec_build_read
    """
    # Используем функцию со статистикой
    result = await spec_build_service.get_spec_build_with_stats(
        spec_build_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=SpecBuildResponse)
async def create_spec_build(
    spec_build_data: SpecBuildCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый тип строения
    
    Требуется право: spec_build_create
    """
    spec_build = await spec_build_service.create_spec_build(
        spec_build_data,
        current_user
    )
    
    return {
        "id": spec_build.id,
        "name": spec_build.name,
        "organizations_count": 0,
        "objects_count": 0
    }

@router.put("/{spec_build_id}", response_model=SpecBuildResponse)
async def update_spec_build(
    spec_build_id: int,
    spec_build_data: SpecBuildUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить тип строения
    
    Требуется право: spec_build_modify
    """
    spec_build = await spec_build_service.update_spec_build(
        spec_build_id,
        spec_build_data,
        current_user
    )
    
    # Получаем статистику для ответа
    async with spec_build_service.new_session() as session:
        organizations_count = await spec_build_service.spec_build_data.count_organizations(
            session, 
            spec_build_id
        )
        objects_count = await spec_build_service.spec_build_data.count_objects(
            session, 
            spec_build_id
        )
    
    return {
        "id": spec_build.id,
        "name": spec_build.name,
        "organizations_count": organizations_count,
        "objects_count": objects_count
    }

@router.delete("/{spec_build_id}")
async def delete_spec_build(
    spec_build_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить тип строения
    
    Требуется право: spec_build_delete
    """
    await spec_build_service.delete_spec_build(
        spec_build_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Тип строения с id {spec_build_id} успешно удален"
    }