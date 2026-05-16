from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_equipment import Spec_Equipment
from data import spec_equipment as spec_equipment_data
from schema.spec_equipment import SpecEquipmentCreate, SpecEquipmentUpdate
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
    
    Args:
        current_user: Текущий пользователь
        permission: Название права (spec_equipment_read, spec_equipment_create и т.д.)
        action: Описание действия для сообщения об ошибке
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

async def get_spec_equipment_by_id(
                                    spec_equipment_id: int,
                                    current_user: User,
                                    load_equipments: bool = False
                                    ) -> Spec_Equipment:
    """
    Получить тип оборудования по ID с проверкой прав
    """
    await check_permission(current_user, "spec_equipment_read", "просмотра типов оборудования")
    
    async with new_session() as session:
        spec_equipment = await spec_equipment_data.get_spec_equipment_by_id(
                                                                            session, 
                                                                            spec_equipment_id, 
                                                                            load_equipments=load_equipments
                                                                            )
        
        if not spec_equipment:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип оборудования с id {spec_equipment_id} не найден"
                                )
        
        return spec_equipment

async def get_spec_equipments_paginated(
                                        pagination: PaginationParams,
                                        current_user: User,
                                        search: Optional[str] = None,
                                        sort_by: str = "name",
                                        sort_order: str = "asc"
                                        ) -> Tuple[List[Spec_Equipment], int]:
    """
    Получить список типов оборудования с пагинацией
    """
    await check_permission(current_user, "spec_equipment_read", "просмотра списка типов оборудования")
    
    async with new_session() as session:
        items, total = await spec_equipment_data.get_spec_equipment_paginated(
                                                                                session=session,
                                                                                skip=pagination.skip,
                                                                                limit=pagination.limit,
                                                                                search=search,
                                                                                sort_by=sort_by,
                                                                                sort_order=sort_order,
                                                                                load_equipments=True  # Загружаем связанное оборудование для подсчета
                                                                                )
        
        return items, total

async def get_all_spec_equipments(
                                    current_user: User,
                                    load_equipments: bool = False
                                    ) -> List[Spec_Equipment]:
    """
    Получить все типы оборудования
    """
    await check_permission(current_user, "spec_equipment_read", "просмотра типов оборудования")
    
    async with new_session() as session:
        return await spec_equipment_data.get_spec_equipment_all(
                                                                session,
                                                                load_equipments=load_equipments)

async def get_spec_equipment_options(
                                    current_user: User
                                    ) -> List[Spec_Equipment]:
    """
    Получить минимальную информацию о типах оборудования для выпадающих списков
    """
    await check_permission(current_user, "spec_equipment_read", "просмотра типов оборудования")
    
    async with new_session() as session:
        return await spec_equipment_data.get_spec_equipment_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_equipment_with_stats(
                                        spec_equipment_id: int,
                                        current_user: User
                                        ) -> dict:
    """
    Получить тип оборудования со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "spec_equipment_read", "просмотра типов оборудования")
    
    async with new_session() as session:
        # Получаем тип оборудования (без загрузки оборудования)
        spec_equipment = await spec_equipment_data.get_spec_equipment_by_id(
                                                                            session, 
                                                                            spec_equipment_id,
                                                                            load_equipments=False
                                                                            )
        
        if not spec_equipment:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип оборудования с id \
                                {spec_equipment_id} не найден"
                                )
        
        # Получаем ТОЛЬКО количество связанного оборудования
        equipments_count = await spec_equipment_data.count_spec_equipment_equipments(
                                                                                    session, 
                                                                                    spec_equipment_id
                                                                                    )
        
        # Возвращаем готовый словарь для ответа
        return {
                "id": spec_equipment.id,
                "name": spec_equipment.name,
                "equipments_count": equipments_count
                }

async def update_spec_equipment_with_stats(
                                            spec_equipment_id: int,
                                            spec_equipment_update: SpecEquipmentUpdate,
                                            current_user: User
                                            ) -> dict:
    """
    Обновить тип оборудования и вернуть словарь со статистикой для ответа
    """
    await check_permission(current_user, "spec_equipment_modify", "изменения типов оборудования")

    async with new_session() as session:
        existing = await spec_equipment_data.get_spec_equipment_by_id(
                                                                        session,
                                                                        spec_equipment_id
                                                                        )
        if not existing:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип оборудования с id {spec_equipment_id} не найден"
                                )

        if spec_equipment_update.name and spec_equipment_update.name != existing.name:
            if await spec_equipment_data.check_spec_equipment_name_exists(
                                                                            session,
                                                                            spec_equipment_update.name,
                                                                            spec_equipment_id
                                                                            ):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Тип оборудования с названием "
                                           f"'{spec_equipment_update.name}' уже существует"
                                    )

        spec_equipment = await spec_equipment_data.update_spec_equipment(
                                                                            session,
                                                                            spec_equipment_id,
                                                                            spec_equipment_update
                                                                            )

        equipments_count = await spec_equipment_data.count_spec_equipment_equipments(
                                                                                        session,
                                                                                        spec_equipment_id
                                                                                        )

        return {
                "id": spec_equipment.id,
                "name": spec_equipment.name,
                "equipments_count": equipments_count
                }

async def get_spec_equipments_paginated_with_stats(
                                                    pagination: PaginationParams,
                                                    current_user: User,
                                                    search: Optional[str] = None,
                                                    sort_by: str = "name",
                                                    sort_order: str = "asc"
                                                    ) -> Tuple[List[dict], int]:
    """
    Получить список типов оборудования со статистикой для ответа
    """
    await check_permission(current_user, "spec_equipment_read", "просмотра списка типов оборудования")
    
    async with new_session() as session:
        # Получаем типы оборудования (без загрузки оборудования)
        items, total = await spec_equipment_data.get_spec_equipment_paginated(
                                                                                session=session,
                                                                                skip=pagination.skip,
                                                                                limit=pagination.limit,
                                                                                search=search,
                                                                                sort_by=sort_by,
                                                                                sort_order=sort_order,
                                                                                load_equipments=False
                                                                                )
        
        # Для каждого типа оборудования получаем количество оборудования
        result_items = []
        for item in items:
            equipments_count = await spec_equipment_data.count_spec_equipment_equipments(
                                                                                            session, 
                                                                                            item.id
                                                                                            )
            result_items.append({
                                "id": item.id,
                                "name": item.name,
                                "equipments_count": equipments_count
                                })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_equipment(
                                spec_equipment_create: SpecEquipmentCreate,
                                current_user: User
                                ) -> Spec_Equipment:
    """
    Создать новый тип оборудования
    """
    await check_permission(current_user, "spec_equipment_create", "создания типов оборудования")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await spec_equipment_data.check_spec_equipment_name_exists(
                                                                        session,
                                                                        spec_equipment_create.name
                                                                        ):
            raise HTTPException(
                                status_code=400,
                                detail=f"Тип оборудования с названием \
                                '{spec_equipment_create.name}' уже существует"
                                )
        
        # Создание
        spec_equipment = await spec_equipment_data.create_spec_equipment(
                                                                            session,
                                                                            spec_equipment_create
                                                                            )
        
        return spec_equipment

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_equipment(
                                spec_equipment_id: int,
                                spec_equipment_update: SpecEquipmentUpdate,
                                current_user: User
                                ) -> Spec_Equipment:
    """
    Обновить тип оборудования
    """
    await check_permission(current_user, "spec_equipment_modify", "изменения типов оборудования")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await spec_equipment_data.get_spec_equipment_by_id(
                                                                        session,
                                                                        spec_equipment_id)
        if not existing:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип оборудования с id \
                                {spec_equipment_id} не найден"
                                )
        
        # Проверка уникальности названия, если оно меняется
        if spec_equipment_update.name and spec_equipment_update.name != existing.name:
            if await spec_equipment_data.check_spec_equipment_name_exists(
                                                                            session,
                                                                            spec_equipment_update.name,
                                                                            spec_equipment_id
                                                                            ):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Тип оборудования с названием \
                                    '{spec_equipment_update.name}' уже существует"
                                    )
        
        # Обновление
        spec_equipment = await spec_equipment_data.update_spec_equipment(
                                                                            session,
                                                                            spec_equipment_id,
                                                                            spec_equipment_update
                                                                            )
        
        return spec_equipment

# ========== УДАЛЕНИЕ ==========

async def delete_spec_equipment(
                                spec_equipment_id: int,
                                current_user: User
                                ) -> bool:
    """
    Удалить тип оборудования
    """
    await check_permission(current_user, "spec_equipment_delete", "удаления типов оборудования")
    
    async with new_session() as session:
        # Проверяем существование и связанное оборудование
        spec_equipment = await spec_equipment_data.get_spec_equipment_by_id(
                                                                            session, 
                                                                            spec_equipment_id, 
                                                                            load_equipments=True
                                                                            )
        
        if not spec_equipment:
            raise HTTPException(
                                    status_code=404,
                                    detail=f"Тип оборудования с id \
                                    {spec_equipment_id} не найден"
                                )
        
        # Проверка на наличие связанного оборудования
        if spec_equipment.equipments and len(spec_equipment.equipments) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить тип оборудования \
                                '{spec_equipment.name}': есть связанное оборудование \
                                ({len(spec_equipment.equipments)} шт.)"
                                )
        
        # Удаление
        success = await spec_equipment_data.delete_spec_equipment(
                                                                    session,
                                                                    spec_equipment_id)
        
        return success