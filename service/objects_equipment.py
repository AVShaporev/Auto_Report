# service/objects_equipment.py

from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.objects_equipment import Objects_Equipment
from data import objects_equipment as link_data
from data import object as object_data
from data import equipment as equipment_data
from schema.objects_equipment import (
    ObjectsEquipmentCreate, 
    ObjectsEquipmentUpdate,
    AddEquipmentToObject,
    UpdateEquipmentCount,
    EquipmentOnObjectResponse
)
from schema.pagination import PaginationParams
from database.database import new_session

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def check_permission(
    current_user: User,
    permission: str,
    action: str = "выполнения операции"
) -> None:
    """
    Проверка наличия права у пользователя
    """
    if not hasattr(current_user.role, permission):
        raise HTTPException(
            status_code=500,
            detail=f"Право {permission} не определено в системе"
        )
    
    has_permission = getattr(current_user.role, permission)
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=f"Недостаточно прав для {action}"
        )

# ========== ПОЛУЧЕНИЕ ==========

async def get_link_by_id(
    link_id: int,
    current_user: User,
    load_relations: bool = False
) -> Objects_Equipment:
    """
    Получить запись связи по ID
    """
    await check_permission(current_user, "object_equipment_read", "просмотра связей объект-оборудование")
    
    async with new_session() as session:
        link = await link_data.get_by_id(session, link_id, load_relations=load_relations)
        
        if not link:
            raise HTTPException(
                status_code=404,
                detail=f"Запись связи с id {link_id} не найдена"
            )
        
        return link

async def get_links_by_object(
    object_id: int,
    current_user: User
) -> List[Objects_Equipment]:
    """
    Получить всё оборудование для конкретного объекта
    """
    await check_permission(current_user, "object_equipment_read", "просмотра оборудования на объекте")
    
    async with new_session() as session:
        # Проверяем существование объекта
        obj = await object_data.get_by_id(session, object_id)
        if not obj:
            raise HTTPException(
                status_code=404,
                detail=f"Объект с id {object_id} не найден"
            )
        
        links = await link_data.get_by_object(session, object_id, load_relations=True)
        return links

async def get_links_by_equipment(
    equipment_id: int,
    current_user: User
) -> List[Objects_Equipment]:
    """
    Получить все объекты, где используется конкретное оборудование
    """
    await check_permission(current_user, "object_equipment_read", "просмотра объектов с оборудованием")
    
    async with new_session() as session:
        # ✅ ИСПРАВЛЕНО: используем правильную функцию для проверки оборудования
        equipment = await equipment_data.get_by_id(session, equipment_id)
        if not equipment:
            raise HTTPException(
                status_code=404,
                detail=f"Оборудование с id {equipment_id} не найдено"
            )
        
        links = await link_data.get_by_equipment(session, equipment_id, load_relations=True)
        return links

async def get_links_paginated(
    pagination: PaginationParams,
    current_user: User,
    object_id: Optional[int] = None,
    equipment_id: Optional[int] = None,
    sort_by: str = "id",
    sort_order: str = "asc"
) -> Tuple[List[Objects_Equipment], int]:
    """
    Получить список связей с пагинацией
    """
    await check_permission(current_user, "object_equipment_read", "просмотра списка связей")
    
    async with new_session() as session:
        items, total = await link_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            object_id=object_id,
            equipment_id=equipment_id,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )
        
        return items, total

# ========== ПОЛУЧЕНИЕ С ДЕТАЛЬНОЙ ИНФОРМАЦИЕЙ ==========

async def get_equipment_on_object(
    object_id: int,
    current_user: User
) -> List[dict]:
    """
    Получить оборудование на объекте в удобном формате
    """
    await check_permission(current_user, "object_equipment_read", "просмотра оборудования на объекте")
    
    async with new_session() as session:
        # Проверяем существование объекта
        obj = await object_data.get_by_id(session, object_id)
        if not obj:
            raise HTTPException(
                status_code=404,
                detail=f"Объект с id {object_id} не найден"
            )
        
        links = await link_data.get_by_object(session, object_id, load_relations=True)
        
        result = []
        for link in links:
            result.append({
                "id": link.id,
                "equipment_id": link.equipment_id,
                "equipment_name": link.equipment.name if link.equipment else None,
                "inventory_number": link.equipment.inventory_number if link.equipment else None,
                "serial_number": link.equipment.serial_number if link.equipment else None,
                "count": link.count,
                "installation_date": link.equipment.installation_date if link.equipment else None,
                "is_active": link.equipment.is_active if link.equipment else None
            })
        
        return result

async def get_link_with_details(
    link_id: int,
    current_user: User
) -> dict:
    """
    Получить запись связи с детальной информацией
    """
    await check_permission(current_user, "object_equipment_read", "просмотра связей")
    
    async with new_session() as session:
        link = await link_data.get_by_id(session, link_id, load_relations=True)
        
        if not link:
            raise HTTPException(
                status_code=404,
                detail=f"Запись связи с id {link_id} не найдена"
            )
        
        return {
            "id": link.id,
            "object_id": link.object_id,
            "equipment_id": link.equipment_id,
            "count": link.count,
            "object_name": link.object.name if link.object else None,
            "equipment_name": link.equipment.name if link.equipment else None,
            "equipment_inventory_number": link.equipment.inventory_number if link.equipment else None,
            "equipment_serial_number": link.equipment.serial_number if link.equipment else None,
            "equipment_installation_date": link.equipment.installation_date if link.equipment else None,
            "equipment_is_active": link.equipment.is_active if link.equipment else None
        }

# ========== СОЗДАНИЕ ==========

async def add_equipment_to_object(
    object_id: int,
    add_data: AddEquipmentToObject,
    current_user: User
) -> Objects_Equipment:
    """
    Добавить оборудование на объект
    """
    await check_permission(current_user, "object_equipment_create", "добавления оборудования на объект")
    
    async with new_session() as session:
        # Проверяем существование объекта
        obj = await object_data.get_by_id(session, object_id)
        if not obj:
            raise HTTPException(
                status_code=404,
                detail=f"Объект с id {object_id} не найден"
            )
        
        # ✅ ИСПРАВЛЕНО: используем правильную функцию для проверки оборудования
        equipment = await equipment_data.get_by_id(session, add_data.equipment_id)
        if not equipment:
            raise HTTPException(
                status_code=404,
                detail=f"Оборудование с id {add_data.equipment_id} не найдено"
            )
        
        # Проверяем, активно ли оборудование
        if equipment and not equipment.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Оборудование '{equipment.name}' списано и не может быть добавлено на объект"
            )
        
        # Проверяем, не добавлено ли уже это оборудование на объект
        existing = await link_data.get_by_object_and_equipment(
            session, object_id, add_data.equipment_id
        )
        
        if existing:
            # Если уже есть, обновляем количество
            existing.count += add_data.count
            await session.commit()
            await session.refresh(existing)
            return existing
        
        # Создаем новую связь
        link_create = ObjectsEquipmentCreate(
            object_id=object_id,
            equipment_id=add_data.equipment_id,
            count=add_data.count
        )
        
        link = await link_data.create(session, link_create)
        return link

# ========== ОБНОВЛЕНИЕ ==========

async def update_equipment_on_object(
    link_id: int,
    update_data: ObjectsEquipmentUpdate,
    current_user: User
) -> Objects_Equipment:
    """
    Обновить информацию об оборудовании на объекте
    """
    await check_permission(current_user, "object_equipment_modify", "изменения оборудования на объекте")
    
    async with new_session() as session:
        # Проверяем существование записи
        existing = await link_data.get_by_id(session, link_id, load_relations=True)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Запись связи с id {link_id} не найдена"
            )
        
        # Если меняется оборудование, проверяем его существование
        if update_data.equipment_id and update_data.equipment_id != existing.equipment_id:
            # ✅ ИСПРАВЛЕНО: используем правильную функцию
            equipment = await equipment_data.get_by_id(session, update_data.equipment_id)
            if not equipment:
                raise HTTPException(
                    status_code=400,
                    detail=f"Оборудование с id {update_data.equipment_id} не существует"
                )
            
            # Проверяем, активно ли новое оборудование
            if equipment and not equipment.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"Оборудование '{equipment.name}' списано и не может быть добавлено на объект"
                )
            
            # Проверяем, нет ли уже такой связки
            duplicate = await link_data.get_by_object_and_equipment(
                session, existing.object_id, update_data.equipment_id
            )
            if duplicate and duplicate.id != link_id:
                raise HTTPException(
                    status_code=400,
                    detail="Это оборудование уже добавлено на объект"
                )
        
        # Обновление
        link = await link_data.update(session, link_id, update_data)
        return link

async def update_equipment_count(
    object_id: int,
    equipment_id: int,
    count_data: UpdateEquipmentCount,
    current_user: User
) -> Objects_Equipment:
    """
    Обновить количество конкретного оборудования на объекте
    """
    await check_permission(current_user, "object_equipment_modify", "изменения количества оборудования")
    
    async with new_session() as session:
        link = await link_data.update_count(
            session, 
            object_id, 
            equipment_id, 
            count_data.count
        )
        
        if not link:
            raise HTTPException(
                status_code=404,
                detail=f"Оборудование с id {equipment_id} не найдено на объекте {object_id}"
            )
        
        return link

# ========== УДАЛЕНИЕ ==========

async def remove_equipment_from_object(
    link_id: int,
    current_user: User
) -> bool:
    """
    Удалить оборудование с объекта
    """
    await check_permission(current_user, "object_equipment_delete", "удаления оборудования с объекта")
    
    async with new_session() as session:
        # Проверяем существование записи
        link = await link_data.get_by_id(session, link_id)
        if not link:
            raise HTTPException(
                status_code=404,
                detail=f"Запись связи с id {link_id} не найдена"
            )
        
        success = await link_data.delete(session, link_id)
        return success

async def remove_specific_equipment(
    object_id: int,
    equipment_id: int,
    current_user: User
) -> bool:
    """
    Удалить конкретное оборудование с объекта
    """
    await check_permission(current_user, "object_equipment_delete", "удаления оборудования с объекта")
    
    async with new_session() as session:
        success = await link_data.delete_by_object_and_equipment(session, object_id, equipment_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Оборудование с id {equipment_id} не найдено на объекте {object_id}"
            )
        
        return success