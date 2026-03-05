from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.object import (
    ObjectCreate,
    ObjectUpdate,
    ObjectResponse,
    ObjectListResponse,
    ObjectOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import object as object_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/object", tags=["object"])

@router.get("/list", response_model=PaginatedResponse[ObjectListResponse])
async def get_object_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию или ответственному лицу"),
    region_id: Optional[int] = Query(None, ge=1, description="Фильтр по региону"),
    arial_id: Optional[int] = Query(None, ge=1, description="Фильтр по району"),
    locality_id: Optional[int] = Query(None, ge=1, description="Фильтр по населенному пункту"),
    street_id: Optional[int] = Query(None, ge=1, description="Фильтр по улице"),
    contract_id: Optional[int] = Query(None, ge=1, description="Фильтр по контракту"),
    period_id: Optional[int] = Query(None, ge=1, description="Фильтр по периоду"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список объектов с пагинацией
    
    Требуется право: object_read
    """
    items, total = await object_service.get_objects_paginated_with_stats(
        pagination=pagination,
        current_user=current_user,
        search=search,
        region_id=region_id,
        arial_id=arial_id,
        locality_id=locality_id,
        street_id=street_id,
        contract_id=contract_id,
        period_id=period_id,
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

@router.get("/options", response_model=List[ObjectOptionResponse])
async def get_object_options(
    contract_id: Optional[int] = Query(None, ge=1, description="Фильтр по контракту"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список объектов для выпадающих списков
    
    Требуется право: object_read
    """
    objects = await object_service.get_object_options(current_user)
    
    result = []
    for obj in objects:
        # Формируем краткий адрес
        address_parts = []
        if obj.locality:
            address_parts.append(obj.locality.name)
        if obj.street:
            address_parts.append(obj.street.name)
        if obj.build_number:
            address_parts.append(f"д.{obj.build_number}")
        address = ", ".join(address_parts) if address_parts else None
        
        result.append({
            "id": obj.id,
            "name": obj.name,
            "address": address
        })
    
    return result

@router.get("/all", response_model=List[ObjectListResponse])
async def get_all_objects(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все объекты (без пагинации)
    
    Требуется право: object_read
    """
    objects = await object_service.get_all_objects(
        current_user,
        load_relations=True
    )
    
    result = []
    for obj in objects:
        # Формируем адрес
        address_parts = []
        if obj.locality:
            address_parts.append(obj.locality.name)
        if obj.street:
            address_parts.append(obj.street.name)
        if obj.build_number:
            address_parts.append(f"д.{obj.build_number}")
        address = ", ".join(address_parts) if address_parts else None
        
        result.append({
            "id": obj.id,
            "name": obj.name,
            "build_number": obj.build_number,
            "room_number": obj.room_number,
            "responsible_face": obj.responsible_face,
            "region_name": obj.region.name if obj.region else None,
            "locality_name": obj.locality.name if obj.locality else None,
            "street_name": obj.street.name if obj.street else None,
            "contract_number": obj.contract.number if obj.contract else None,
            "equipments_count": len(obj.objects_equipments) if obj.objects_equipments else 0,
            "address": address
        })
    
    return result

@router.get("/{object_id}", response_model=ObjectResponse)
async def get_object_by_id(
    object_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить объект по ID
    
    Требуется право: object_read
    """
    # Используем функцию со статистикой
    result = await object_service.get_object_with_stats(
        object_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=ObjectResponse)
async def create_object(
    object_data: ObjectCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый объект
    
    Требуется право: object_create
    """
    obj = await object_service.create_object(
        object_data,
        current_user
    )
    
    return {
        "id": obj.id,
        "name": obj.name,
        "build_number": obj.build_number,
        "room_number": obj.room_number,
        "responsible_face": obj.responsible_face,
        "responsible_faces_contact": obj.responsible_faces_contact,
        "region_id": obj.region_id,
        "arial_id": obj.arial_id,
        "locality_id": obj.locality_id,
        "street_id": obj.street_id,
        "spec_build_id": obj.spec_build_id,
        "spec_room_id": obj.spec_room_id,
        "period_id": obj.period_id,
        "contract_id": obj.contract_id,
        "region_name": None,
        "arial_name": None,
        "locality_name": None,
        "street_name": None,
        "spec_build_name": None,
        "spec_room_name": None,
        "period_name": None,
        "contract_number": None,
        "equipments_count": 0,
        "reports_count": 0,
        "orders_count": 0
    }

@router.put("/{object_id}", response_model=ObjectResponse)
async def update_object(
    object_id: int,
    object_data: ObjectUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить объект
    
    Требуется право: object_modify
    """
    obj = await object_service.update_object(
        object_id,
        object_data,
        current_user
    )
    
    # Получаем статистику для ответа
    async with object_service.new_session() as session:
        equipments_count = await object_service.object_data.count_equipments(
            session, 
            object_id
        )
        reports_count = await object_service.object_data.count_reports(
            session, 
            object_id
        )
        orders_count = await object_service.object_data.count_orders(
            session, 
            object_id
        )
    
    return {
        "id": obj.id,
        "name": obj.name,
        "build_number": obj.build_number,
        "room_number": obj.room_number,
        "responsible_face": obj.responsible_face,
        "responsible_faces_contact": obj.responsible_faces_contact,
        "region_id": obj.region_id,
        "arial_id": obj.arial_id,
        "locality_id": obj.locality_id,
        "street_id": obj.street_id,
        "spec_build_id": obj.spec_build_id,
        "spec_room_id": obj.spec_room_id,
        "period_id": obj.period_id,
        "contract_id": obj.contract_id,
        "region_name": obj.region.name if obj.region else None,
        "arial_name": obj.arial.name if obj.arial else None,
        "locality_name": obj.locality.name if obj.locality else None,
        "street_name": obj.street.name if obj.street else None,
        "spec_build_name": obj.spec_build.name if obj.spec_build else None,
        "spec_room_name": obj.spec_room.name if obj.spec_room else None,
        "period_name": obj.period.name if obj.period else None,
        "contract_number": obj.contract.number if obj.contract else None,
        "equipments_count": equipments_count,
        "reports_count": reports_count,
        "orders_count": orders_count
    }

@router.delete("/{object_id}")
async def delete_object(
    object_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить объект
    
    Требуется право: object_delete
    """
    await object_service.delete_object(
        object_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Объект с id {object_id} успешно удален"
    }