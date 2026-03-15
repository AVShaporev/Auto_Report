from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_equipment import (
                                    SpecEquipmentCreate,
                                    SpecEquipmentUpdate,
                                    SpecEquipmentResponse,
                                    SpecEquipmentListResponse,
                                    SpecEquipmentOptionResponse
                                    )
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_equipment as spec_equipment_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_equipment", tags=["spec_equipment"])

@router.get("/list", response_model=PaginatedResponse[SpecEquipmentListResponse])
async def get_spec_equipment_list(
                                    pagination: PaginationParams = Depends(),
                                    search: Optional[str] = Query(None, description="Поиск по названию"),
                                    sort_by: str = Query("name", description="Поле сортировки"),
                                    sort_order: str = Query("asc", regex="^(asc|desc)$"),
                                    current_user: User = Depends(get_current_active_user)
                                    ):
    """
    Получить список типов оборудования с пагинацией
    
    Требуется право: spec_equipment_read
    """
    items, total = await spec_equipment_service.get_spec_equipments_paginated_with_stats(
                                                                            pagination=pagination,
                                                                            current_user=current_user,
                                                                            search=search,
                                                                            sort_by=sort_by,
                                                                            sort_order=sort_order
                                                                        )
    
    pages = (total + pagination.limit - 1) // pagination.limit

    print(pagination)
    print(items)
    
    return PaginatedResponse(
                            items=items,
                            total=total,
                            page=pagination.page,
                            per_page=pagination.limit,
                            pages=pages
                            )

@router.get("/options", response_model=List[SpecEquipmentOptionResponse])
async def get_spec_equipment_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов оборудования для выпадающих списков
    
    Требуется право: spec_equipment_read
    """
    spec_equipments = await spec_equipment_service.get_spec_equipment_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name
        }
        for item in spec_equipments
    ]

@router.get("/all", response_model=List[SpecEquipmentListResponse])
async def get_all_spec_equipments(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все типы оборудования (без пагинации)
    
    Требуется право: spec_equipment_read
    """
    spec_equipments = await spec_equipment_service.get_all_spec_equipments(
        current_user,
        load_equipments=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "equipments_count": len(item.equipments) if item.equipments else 0
        }
        for item in spec_equipments
    ]

@router.get("/{spec_equipment_id}", response_model=SpecEquipmentResponse)
async def get_spec_equipment_by_id(
    spec_equipment_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить тип оборудования по ID
    
    Требуется право: spec_equipment_read
    """
    # Используем функцию со статистикой
    result = await spec_equipment_service.get_spec_equipment_with_stats(
        spec_equipment_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=SpecEquipmentResponse)
async def create_spec_equipment(
    spec_equipment_data: SpecEquipmentCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый тип оборудования
    
    Требуется право: spec_equipment_create
    """
    spec_equipment = await spec_equipment_service.create_spec_equipment(
        spec_equipment_data,
        current_user
    )
    
    return {
        "id": spec_equipment.id,
        "name": spec_equipment.name,
        "equipments_count": 0
    }

@router.put("/{spec_equipment_id}", response_model=SpecEquipmentResponse)
async def update_spec_equipment(
    spec_equipment_id: int,
    spec_equipment_data: SpecEquipmentUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить тип оборудования
    
    Требуется право: spec_equipment_modify
    """
    spec_equipment = await spec_equipment_service.update_spec_equipment(
        spec_equipment_id,
        spec_equipment_data,
        current_user
    )
    
    # Получаем количество связанного оборудования для ответа
    async with spec_equipment_service.new_session() as session:
        equipments_count = await spec_equipment_service.spec_equipment_data.count_equipments(
            session, 
            spec_equipment_id
        )
    
    return {
        "id": spec_equipment.id,
        "name": spec_equipment.name,
        "equipments_count": equipments_count
    }

@router.delete("/{spec_equipment_id}")
async def delete_spec_equipment(
    spec_equipment_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить тип оборудования
    
    Требуется право: spec_equipment_delete
    """
    await spec_equipment_service.delete_spec_equipment(
        spec_equipment_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Тип оборудования с id {spec_equipment_id} успешно удален"
    }