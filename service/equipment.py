from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.equipment import Equipment
from data import equipment as equipment_data
from service.activity_log import log_activity
from schema.equipment import EquipmentCreate, EquipmentUpdate
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

async def get_equipment_by_id(
    equipment_id: int,
    current_user: User,
    load_relations: bool = False
) -> Equipment:
    """
    Получить оборудование по ID с проверкой прав
    """
    await check_permission(current_user, "equipment_read", "просмотра оборудования")

    async with new_session() as session:
        equipment = await equipment_data.get_equipment_by_id(
            session,
            equipment_id,
            load_relations=load_relations
        )

        if not equipment:
            raise HTTPException(
                status_code=404,
                detail=f"Оборудование с id {equipment_id} не найдено"
            )

        return equipment

async def get_equipments_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_equipment_id: Optional[int] = None,
    object_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Equipment], int]:
    """
    Получить список оборудования с пагинацией
    """
    await check_permission(current_user, "equipment_read", "просмотра списка оборудования")

    async with new_session() as session:
        items, total = await equipment_data.get_equipment_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_equipment_id=spec_equipment_id,
            object_id=object_id,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )

        return items, total

async def get_equipment_options(
    current_user: User,
    object_id: Optional[int] = None,
    is_active: Optional[bool] = None
) -> List[Equipment]:
    """
    Получить минимальную информацию об оборудовании для выпадающих списков
    """
    await check_permission(current_user, "equipment_read", "просмотра оборудования")

    async with new_session() as session:
        return await equipment_data.get_equipment_options(
            session,
            object_id=object_id,
            is_active=is_active
        )

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_equipment_with_details(
    equipment_id: int,
    current_user: User
) -> dict:
    """
    Получить оборудование с детальной информацией для ответа
    """
    await check_permission(current_user, "equipment_read", "просмотра оборудования")

    async with new_session() as session:
        equipment = await equipment_data.get_equipment_by_id(
            session,
            equipment_id,
            load_relations=True
        )

        if not equipment:
            raise HTTPException(
                status_code=404,
                detail=f"Оборудование с id {equipment_id} не найдено"
            )

        # Регламент ТО = операции, привязанные к типу оборудования
        # (Spec_Equipment.operations — m2m через operations_spec_equipments).
        operations = []
        if equipment.spec_equipment and equipment.spec_equipment.operations:
            for op in sorted(equipment.spec_equipment.operations, key=lambda o: (o.name or "").lower()):
                operations.append({
                    "id": op.id,
                    "name": op.name,
                    "short_name": op.short_name,
                    "description": op.description,
                })

        return {
            "id": equipment.id,
            "name": equipment.name,
            "is_active": equipment.is_active,
            "spec_equipment_id": equipment.spec_equipment_id,
            "spec_equipment_name": equipment.spec_equipment.name if equipment.spec_equipment else None,
            "spec_system_id": equipment.spec_system_id,
            "spec_system_name": equipment.spec_system.name if equipment.spec_system else None,
            "operations": operations,
        }

async def get_equipments_paginated_with_details(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_equipment_id: Optional[int] = None,
    object_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список оборудования с детальной информацией для ответа
    """
    await check_permission(current_user, "equipment_read", "просмотра списка оборудования")

    async with new_session() as session:
        items, total = await equipment_data.get_equipment_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_equipment_id=spec_equipment_id,
            object_id=object_id,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )

        result_items = []
        for item in items:
            result_items.append({
                "id": item.id,
                "name": item.name,
                "is_active": item.is_active,
                "spec_equipment_name": item.spec_equipment.name if item.spec_equipment else None,
                "spec_system_id": item.spec_system_id,
                "spec_system_name": item.spec_system.name if item.spec_system else None,
            })

        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_equipment(
    equipment_create: EquipmentCreate,
    current_user: User
) -> Equipment:
    """
    Создать новое оборудование
    """
    await check_permission(current_user, "equipment_create", "создания оборудования")

    async with new_session() as session:
        # Проверка уникальности
        if await equipment_data.check_equipment_name_exists(session, equipment_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Оборудование с названием '{equipment_create.name}' уже существует"
            )

        # Проверка существования типа оборудования
        if not await equipment_data.check_equipment_spec_equipment_exists(session, equipment_create.spec_equipment_id):
            raise HTTPException(
                status_code=400,
                detail=f"Тип оборудования с id {equipment_create.spec_equipment_id} не существует"
            )

        equipment = await equipment_data.create_equipment(session, equipment_create)
        await log_activity(
            session, current_user,
            action='create', entity='equipment', entity_id=equipment.id,
            summary=f'Создал оборудование «{equipment.name}»',
        )
        return equipment

# ========== ОБНОВЛЕНИЕ ==========

async def update_equipment(
    equipment_id: int,
    equipment_update: EquipmentUpdate,
    current_user: User
) -> Equipment:
    """
    Обновить оборудование
    """
    await check_permission(current_user, "equipment_modify", "изменения оборудования")

    async with new_session() as session:
        existing = await equipment_data.get_equipment_by_id(session, equipment_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Оборудование с id {equipment_id} не найдено"
            )

        update_data = equipment_update.model_dump(exclude_unset=True)

        # Проверка уникальности при изменении
        if 'name' in update_data and update_data['name'] != existing.name:
            if await equipment_data.check_equipment_name_exists(session, update_data['name'], equipment_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Оборудование с названием '{update_data['name']}' уже существует"
                )

        if 'spec_equipment_id' in update_data and update_data['spec_equipment_id'] != existing.spec_equipment_id:
            if not await equipment_data.check_equipment_spec_equipment_exists(session, update_data['spec_equipment_id']):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип оборудования с id {update_data['spec_equipment_id']} не существует"
                )

        equipment = await equipment_data.update_equipment(session, equipment_id, equipment_update)
        changed_keys = ', '.join(sorted(update_data.keys())) or 'нет полей'
        await log_activity(
            session, current_user,
            action='update', entity='equipment', entity_id=equipment.id,
            summary=f'Изменил оборудование «{equipment.name}»: {changed_keys}',
            details=update_data,
        )
        return equipment

# ========== УДАЛЕНИЕ ==========

async def delete_equipment(
    equipment_id: int,
    current_user: User
) -> bool:
    """
    Удалить оборудование
    """
    await check_permission(current_user, "equipment_delete", "удаления оборудования")

    async with new_session() as session:
        equipment = await equipment_data.get_equipment_by_id(session, equipment_id, load_relations=True)

        if not equipment:
            raise HTTPException(
                status_code=404,
                detail=f"Оборудование с id {equipment_id} не найдено"
            )

        # Проверка на наличие связанных объектов
        if equipment.objects_equipments and len(equipment.objects_equipments) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить оборудование '{equipment.name}': есть связанные объекты"
            )

        equipment_name = equipment.name
        success = await equipment_data.delete_equipment(session, equipment_id)
        if success:
            await log_activity(
                session, current_user,
                action='delete', entity='equipment', entity_id=equipment_id,
                summary=f'Удалил оборудование «{equipment_name}»',
            )
        return success
