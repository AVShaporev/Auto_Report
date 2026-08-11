from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.objects_equipment import (
    ObjectsEquipmentCreate,
    ObjectsEquipmentUpdate,
    ObjectsEquipmentResponse,
    ObjectsEquipmentListResponse,
    ObjectsEquipmentOptionResponse,
    AddEquipmentToObject,
    EquipmentOnObjectResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import objects_equipment as link_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/object-equipment", tags=["object-equipment"])

# ========== ПОЛУЧЕНИЕ СПИСКОВ ==========

@router.get("/list", response_model=PaginatedResponse[ObjectsEquipmentListResponse])
async def get_links_list(
    pagination: PaginationParams = Depends(),
    object_id: Optional[int] = Query(None, ge=1, description="Фильтр по объекту"),
    equipment_id: Optional[int] = Query(None, ge=1, description="Фильтр по оборудованию"),
    sort_by: str = Query("id", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список связей объектов с оборудованием
    
    Требуется право: object_equipment_read
    """
    items, total = await link_service.get_links_paginated(
        pagination=pagination,
        current_user=current_user,
        object_id=object_id,
        equipment_id=equipment_id,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "object_id": item.object_id,
            "equipment_id": item.equipment_id,
            "count": item.count,
            "object_name": item.object.name if item.object else None,
            "equipment_name": item.equipment.name if item.equipment else None
        })
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=result_items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages
    )

# ========== ВЫПАДАЮЩИЙ СПИСОК ==========

@router.get("/options", response_model=List[ObjectsEquipmentOptionResponse])
async def get_objects_equipment_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все связи объект-оборудование для выпадающих списков (без пагинации).

    Нужно фронту для каскадных селектов «Договор → Объект → Оборудование» в форме
    неисправности: /list ограничен per_page<=100 через PaginationParams, поэтому
    не годится когда связей > 100.

    Требуется право: object_equipment_read
    """
    items = await link_service.get_objects_equipment_options(current_user)

    return [
        {
            "id": item.id,
            "object_id": item.object_id,
            "equipment_id": item.equipment_id,
            "equipment_name": item.equipment.name if item.equipment else None,
            "inventory_number": item.inventory_number,
        }
        for item in items
    ]

# ========== ПОЛУЧЕНИЕ ПО ОБЪЕКТУ ==========

@router.get("/by-object/{object_id}", response_model=List[EquipmentOnObjectResponse])
async def get_equipment_on_object(
    object_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить всё оборудование на конкретном объекте
    
    Требуется право: object_equipment_read
    
    Возвращает список оборудования с детальной информацией
    """
    equipment_list = await link_service.get_equipment_on_object(object_id, current_user)
    return equipment_list

# ========== ПОЛУЧЕНИЕ ПО ОБОРУДОВАНИЮ ==========

@router.get("/by-equipment/{equipment_id}", response_model=List[ObjectsEquipmentListResponse])
async def get_objects_with_equipment(
    equipment_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все объекты, где используется конкретное оборудование
    
    Требуется право: object_equipment_read
    """
    links = await link_service.get_links_by_equipment(equipment_id, current_user)
    
    return [
        {
            "id": link.id,
            "object_id": link.object_id,
            "equipment_id": link.equipment_id,
            "count": link.count,
            "object_name": link.object.name if link.object else None,
            "equipment_name": link.equipment.name if link.equipment else None
        }
        for link in links
    ]

# ========== ПОЛУЧЕНИЕ ПО ID ==========

@router.get("/{link_id}", response_model=ObjectsEquipmentResponse)
async def get_link_by_id(
    link_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить запись связи по ID
    
    Требуется право: object_equipment_read
    """
    result = await link_service.get_link_with_details(link_id, current_user)
    return result

# ========== ДОБАВЛЕНИЕ ОБОРУДОВАНИЯ НА ОБЪЕКТ ==========

@router.post("/add-to-object/{object_id}", response_model=ObjectsEquipmentResponse)
async def add_equipment_to_object(
    object_id: int,
    add_data: AddEquipmentToObject,
    current_user: User = Depends(get_current_active_user)
):
    """
    Добавить оборудование на объект
    
    Если оборудование уже есть на объекте, количество будет увеличено
    
    Требуется право: object_equipment_create
    """
    link = await link_service.add_equipment_to_object(object_id, add_data, current_user)
    return await link_service.get_link_with_details(link.id, current_user)

# ========== ОБНОВЛЕНИЕ КОЛИЧЕСТВА ==========

@router.patch("/update-count/{object_id}/{equipment_id}")
async def update_equipment_count(
    object_id: int,
    equipment_id: int,
    count_data: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить количество конкретного оборудования на объекте
    
    Требуется право: object_equipment_modify
    """
    link = await link_service.update_equipment_count(
        object_id, 
        equipment_id, 
        count_data, 
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Количество обновлено до {count_data.count}",
        "data": {
            "object_id": object_id,
            "equipment_id": equipment_id,
            "count": count_data.count
        }
    }

# ========== ОБНОВЛЕНИЕ ЗАПИСИ ==========

@router.put("/{link_id}", response_model=ObjectsEquipmentResponse)
async def update_link(
    link_id: int,
    update_data: ObjectsEquipmentUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить запись связи
    
    Требуется право: object_equipment_modify
    """
    link = await link_service.update_equipment_on_object(link_id, update_data, current_user)
    return await link_service.get_link_with_details(link.id, current_user)

# ========== УДАЛЕНИЕ ==========

@router.delete("/{link_id}")
async def delete_link(
    link_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить запись связи по ID
    
    Требуется право: object_equipment_delete
    """
    await link_service.remove_equipment_from_object(link_id, current_user)
    
    return {
        "status": "success",
        "message": f"Оборудование успешно удалено с объекта"
    }

@router.delete("/remove/{object_id}/{equipment_id}")
async def remove_specific_equipment(
    object_id: int,
    equipment_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить конкретное оборудование с объекта
    
    Требуется право: object_equipment_delete
    """
    await link_service.remove_specific_equipment(object_id, equipment_id, current_user)
    
    return {
        "status": "success",
        "message": f"Оборудование успешно удалено с объекта"
    }