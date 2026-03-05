from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.period import (
    PeriodCreate,
    PeriodUpdate,
    PeriodResponse,
    PeriodListResponse,
    PeriodOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import period as period_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/period", tags=["period"])

@router.get("/list", response_model=PaginatedResponse[PeriodListResponse])
async def get_period_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию или периодичности"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список периодов с пагинацией
    
    Требуется право: period_read
    """
    items, total = await period_service.get_periods_paginated_with_stats(
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

@router.get("/options", response_model=List[PeriodOptionResponse])
async def get_period_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список периодов для выпадающих списков
    
    Требуется право: period_read
    """
    periods = await period_service.get_period_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "period": item.period
        }
        for item in periods
    ]

@router.get("/all", response_model=List[PeriodListResponse])
async def get_all_periods(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все периоды (без пагинации)
    
    Требуется право: period_read
    """
    periods = await period_service.get_all_periods(
        current_user,
        load_relations=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "period": item.period,
            "objects_count": len(item.objects) if item.objects else 0,
            "reports_count": len(item.reports) if item.reports else 0
        }
        for item in periods
    ]

@router.get("/{period_id}", response_model=PeriodResponse)
async def get_period_by_id(
    period_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить период по ID
    
    Требуется право: period_read
    """
    # Используем функцию со статистикой
    result = await period_service.get_period_with_stats(
        period_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=PeriodResponse)
async def create_period(
    period_data: PeriodCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый период
    
    Требуется право: period_create
    """
    period = await period_service.create_period(
        period_data,
        current_user
    )
    
    return {
        "id": period.id,
        "name": period.name,
        "period": period.period,
        "objects_count": 0,
        "reports_count": 0
    }

@router.put("/{period_id}", response_model=PeriodResponse)
async def update_period(
    period_id: int,
    period_data: PeriodUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить период
    
    Требуется право: period_modify
    """
    period = await period_service.update_period(
        period_id,
        period_data,
        current_user
    )
    
    # Получаем статистику для ответа
    async with period_service.new_session() as session:
        objects_count = await period_service.period_data.count_objects(
            session, 
            period_id
        )
        reports_count = await period_service.period_data.count_reports(
            session, 
            period_id
        )
    
    return {
        "id": period.id,
        "name": period.name,
        "period": period.period,
        "objects_count": objects_count,
        "reports_count": reports_count
    }

@router.delete("/{period_id}")
async def delete_period(
    period_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить период
    
    Требуется право: period_delete
    """
    await period_service.delete_period(
        period_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Период с id {period_id} успешно удален"
    }