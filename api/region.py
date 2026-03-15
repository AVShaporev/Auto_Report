from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.region import (
    RegionCreate,
    RegionUpdate,
    RegionResponse,
    RegionListResponse,
    RegionOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import region as region_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/region", tags=["region"])

@router.get("/list", response_model=PaginatedResponse[RegionListResponse])
async def get_region_list(
                        pagination: PaginationParams = Depends(),
                        search: Optional[str] = Query(None, description="Поиск по названию или символу"),
                        spec_region_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу региона"),
                        sort_by: str = Query("name", description="Поле сортировки"),
                        sort_order: str = Query("asc", regex="^(asc|desc)$"),
                        current_user: User = Depends(get_current_active_user)
                        ):
    """
    Получить список регионов с пагинацией
    
    Требуется право: region_read
    """
    items, total = await region_service.get_regions_paginated_with_stats(
                                                                        pagination=pagination,
                                                                        current_user=current_user,
                                                                        search=search,
                                                                        spec_region_id=spec_region_id,
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

@router.get("/options", response_model=List[RegionOptionResponse])
async def get_region_options(
                            current_user: User = Depends(get_current_active_user)
                            ):
    """
    Получить список регионов для выпадающих списков
    
    Требуется право: region_read
    """
    regions = await region_service.get_region_options(current_user)
    
    return [
        {
            "id": region.id,
            "name": region.name,
            "symbol": region.symbol
        }
        for region in regions
    ]

@router.get("/all", response_model=List[RegionListResponse])
async def get_all_regions(
                            current_user: User = Depends(get_current_active_user)
                            ):
    """
    Получить все регионы (без пагинации)
    
    Требуется право: region_read
    """
    regions = await region_service.get_all_regions(current_user)
    return regions

@router.get("/{region_id}", response_model=RegionResponse)
async def get_region_by_id(
                            region_id: int,
                            current_user: User = Depends(get_current_active_user)
                            ):
    """
    Получить регион по ID
    
    Требуется право: region_read
    """
    # Используем функцию со статистикой
    result = await region_service.get_region_with_stats(
                                                        region_id,
                                                        current_user
                                                        )
    
    return result

@router.post("/create", response_model=RegionResponse)
async def create_region(
                        region_data: RegionCreate,
                        current_user: User = Depends(get_current_active_user)
                        ):
    """
    Создать новый регион
    
    Требуется право: region_create
    """
    region = await region_service.create_region(
                                                region_data,
                                                current_user
                                                )
    
    return {
            "id": region.id,
            "name": region.name,
            "symbol": region.symbol,
            "spec_region_id": region.spec_region_id,
            "spec_region_name": None,  # Будет подгружено при следующем запросе
            "organizations_count": 0,
            "objects_count": 0
            }

@router.put("/{region_id}", response_model=RegionResponse)
async def update_region(
                        region_id: int,
                        region_data: RegionUpdate,
                        current_user: User = Depends(get_current_active_user)
                        ):
    """
    Обновить регион
    
    Требуется право: region_modify
    """
    region = await region_service.update_region(
                                                region_id,
                                                region_data,
                                                current_user
                                                )
    
    # Получаем статистику для ответа
    async with region_service.new_session() as session:
        organizations_count = await region_service.region_data.count_organizations(
                                                                                    session, 
                                                                                    region_id
                                                                                    )
        objects_count = await region_service.region_data.count_objects(
                                                                        session, 
                                                                        region_id
                                                                        )
    
    return {
            "id": region.id,
            "name": region.name,
            "symbol": region.symbol,
            "spec_region_id": region.spec_region_id,
            "spec_region_name": None,  # Будет подгружено при следующем запросе
            "organizations_count": organizations_count,
            "objects_count": objects_count
            }

@router.delete("/{region_id}")
async def delete_region(
                        region_id: int,
                        current_user: User = Depends(get_current_active_user)
                        ):
    """
    Удалить регион
    
    Требуется право: region_delete
    """
    await region_service.delete_region(
                                        region_id,
                                        current_user
                                        )
    
    return {
            "status": "success",
            "message": f"Регион с id {region_id} успешно удален"
            }

# Дополнительный эндпоинт для поиска по символу
@router.get("/by-symbol/{symbol}", response_model=RegionResponse)
async def get_region_by_symbol(
                                symbol: str,
                                current_user: User = Depends(get_current_active_user)
                                ):
    """
    Получить регион по символьному коду
    
    Требуется право: region_read
    """
    await region_service.check_permission(current_user, "region_read", "просмотра регионов")
    
    async with region_service.new_session() as session:
        region = await region_service.region_data.get_by_symbol(session, symbol)
        
        if not region:
            raise HTTPException(
                                status_code=404,
                                detail=f"Регион с символом '{symbol}' не найден"
                                )
        
        organizations_count = await region_service.region_data.count_organizations(
                                                                                    session, 
                                                                                    region.id
                                                                                    )
        objects_count = await region_service.region_data.count_objects(
                                                                        session, 
                                                                        region.id
                                                                        )
        
        return {
                "id": region.id,
                "name": region.name,
                "symbol": region.symbol,
                "spec_region_id": region.spec_region_id,
                "spec_region_name": region.spec_region.name if region.spec_region else None,
                "organizations_count": organizations_count,
                "objects_count": objects_count
                }