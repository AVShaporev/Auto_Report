from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.equipment import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    EquipmentListResponse,
    EquipmentOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import equipment as equipment_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/equipment", tags=["equipment"])

@router.get("/list", response_model=PaginatedResponse[EquipmentListResponse])
async def get_equipment_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    spec_equipment_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу оборудования"),
    object_id: Optional[int] = Query(None, ge=1, description="Фильтр по объекту"),
    is_active: Optional[bool] = Query(None, description="Только активное/списанное"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список оборудования с пагинацией

    - **object_id** - если указан, возвращает только оборудование для этого объекта
    """
    items, total = await equipment_service.get_equipments_paginated_with_details(
        pagination=pagination,
        current_user=current_user,
        search=search,
        spec_equipment_id=spec_equipment_id,
        object_id=object_id,
        is_active=is_active,
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

@router.get("/options", response_model=List[EquipmentOptionResponse])
async def get_equipment_options(
    object_id: Optional[int] = Query(None, ge=1, description="Фильтр по объекту"),
    is_active: Optional[bool] = Query(None, description="Только активное оборудование"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список оборудования для выпадающих списков
    """
    equipments = await equipment_service.get_equipment_options(
        current_user,
        object_id=object_id,
        is_active=is_active
    )

    return [
        {
            "id": item.id,
            "name": item.name,
            "is_active": item.is_active
        }
        for item in equipments
    ]

@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment_by_id(
    equipment_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Получить оборудование по ID"""
    result = await equipment_service.get_equipment_with_details(
        equipment_id,
        current_user
    )
    return result

@router.post("/create", response_model=EquipmentResponse)
async def create_equipment(
    equipment_data: EquipmentCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Создать новое оборудование"""
    equipment = await equipment_service.create_equipment(
        equipment_data,
        current_user
    )
    return await equipment_service.get_equipment_with_details(equipment.id, current_user)

@router.put("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    equipment_data: EquipmentUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Обновить оборудование"""
    equipment = await equipment_service.update_equipment(
        equipment_id,
        equipment_data,
        current_user
    )
    return await equipment_service.get_equipment_with_details(equipment.id, current_user)

@router.patch("/{equipment_id}/toggle-active")
async def toggle_equipment_active(
    equipment_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Переключить статус активности оборудования"""
    equipment = await equipment_service.get_equipment_by_id(equipment_id, current_user)
    update_data = EquipmentUpdate(is_active=not equipment.is_active)
    equipment = await equipment_service.update_equipment(equipment_id, update_data, current_user)

    return {
        "status": "success",
        "message": f"Статус оборудования изменен на {'активно' if equipment.is_active else 'списано'}"
    }

@router.delete("/{equipment_id}")
async def delete_equipment(
    equipment_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Удалить оборудование"""
    await equipment_service.delete_equipment(
        equipment_id,
        current_user
    )
    return {
        "status": "success",
        "message": f"Оборудование с id {equipment_id} успешно удалено"
    }
