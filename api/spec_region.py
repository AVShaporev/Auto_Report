from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_region import (
                                SpecRegionCreate,
                                SpecRegionUpdate,
                                SpecRegionResponse,
                                SpecRegionListResponse,
                                SpecRegionOptionResponse
                                )
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_region as spec_region_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_region", tags=["spec_region"])

@router.get("/list", response_model=PaginatedResponse[SpecRegionListResponse])
async def get_spec_region_list(
                                pagination: PaginationParams = Depends(),
                                search: Optional[str] = Query(None, description="Поиск по названию"),
                                sort_by: str = Query("name", description="Поле сортировки"),
                                sort_order: str = Query("asc", regex="^(asc|desc)$"),
                                current_user: User = Depends(get_current_active_user)
                                ):
    """
    Получить список типов регионов с пагинацией
    
    Требуется право: spec_region_read
    """
    items, total = await spec_region_service.get_spec_regions_paginated_with_stats(
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

@router.get("/options", response_model=List[SpecRegionOptionResponse])
async def get_spec_region_options(
                                    current_user: User = Depends(get_current_active_user)
                                    ):
    """
    Получить список типов регионов для выпадающих списков
    
    Требуется право: spec_region_read
    """
    spec_regions = await spec_region_service.get_spec_region_options(current_user)
    
    return [
                {
                    "id": item.id,
                    "name": item.name
                }
                for item in spec_regions
            ]

@router.get("/all", response_model=List[SpecRegionListResponse])
async def get_all_spec_regions(
                                current_user: User = Depends(get_current_active_user)
                                ):
    """
    Получить все типы регионов (без пагинации)
    
    Требуется право: spec_region_read
    """
    spec_regions = await spec_region_service.get_all_spec_regions(
                                                                    current_user,
                                                                    load_regions=False
                                                                    )
    
    return spec_regions

@router.get("/{spec_region_id}", response_model=SpecRegionResponse)
async def get_spec_region_by_id(
                                spec_region_id: int,
                                current_user: User = Depends(get_current_active_user)
                                ):
    """
    Получить тип региона по ID
    
    Требуется право: spec_region_read
    """
    # Используем функцию со статистикой
    result = await spec_region_service.get_spec_region_with_stats(
                                                                    spec_region_id,
                                                                    current_user
                                                                    )
    
    return result

@router.post("/create", response_model=SpecRegionResponse)
async def create_spec_region(
                                spec_region_data: SpecRegionCreate,
                                current_user: User = Depends(get_current_active_user)
                                ):
    """
    Создать новый тип региона
    
    Требуется право: spec_region_create
    """
    spec_region = await spec_region_service.create_spec_region(
                                                                spec_region_data,
                                                                current_user
                                                                )
    
    return {
            "id": spec_region.id,
            "name": spec_region.name,
            "regions_count": 0
            }

@router.put("/{spec_region_id}", response_model=SpecRegionResponse)
async def update_spec_region(
                            spec_region_id: int,
                            spec_region_data: SpecRegionUpdate,
                            current_user: User = Depends(get_current_active_user)
                            ):
    """
    Обновить тип региона
    
    Требуется право: spec_region_modify
    """
    spec_region = await spec_region_service.update_spec_region(
                                                                spec_region_id,
                                                                spec_region_data,
                                                                current_user
                                                                )
    
    # Получаем количество связанных регионов для ответа
    async with spec_region_service.new_session() as session:
        regions_count = await spec_region_service.spec_region_data.count_regions(
                                                                                session, 
                                                                                spec_region_id
                                                                                )
    
    return {
            "id": spec_region.id,
            "name": spec_region.name,
            "regions_count": regions_count
            }

@router.delete("/{spec_region_id}")
async def delete_spec_region(
                            spec_region_id: int,
                            current_user: User = Depends(get_current_active_user)
                            ):
    """
    Удалить тип региона
    
    Требуется право: spec_region_delete
    """
    await spec_region_service.delete_spec_region(
                                                spec_region_id,
                                                current_user
                                                )
    
    return {
        "status": "success",
        "message": f"Тип региона с id {spec_region_id} успешно удален"
    }