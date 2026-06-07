from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_room import Spec_Room
from data import spec_room as spec_room_data
from schema.spec_room import SpecRoomCreate, SpecRoomUpdate
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
        permission: Название права (spec_room_read, spec_room_create и т.д.)
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

async def get_spec_room_by_id(
    spec_room_id: int,
    current_user: User,
    load_relations: bool = False
) -> Spec_Room:
    """
    Получить тип помещения по ID с проверкой прав
    """
    await check_permission(current_user, "spec_room_read", "просмотра типов помещений")
    
    async with new_session() as session:
        spec_room = await spec_room_data.get_spec_room_by_id(
            session, 
            spec_room_id, 
            load_relations=load_relations
        )
        
        if not spec_room:
            raise HTTPException(
                status_code=404,
                detail=f"Тип помещения с id {spec_room_id} не найден"
            )
        
        return spec_room

async def get_spec_rooms_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Spec_Room], int]:
    """
    Получить список типов помещений с пагинацией
    """
    await check_permission(current_user, "spec_room_read", "просмотра списка типов помещений")
    
    async with new_session() as session:
        items, total = await spec_room_data.get_spec_room_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True  # Загружаем связанные данные для подсчета
        )
        
        return items, total

async def get_all_spec_rooms(
    current_user: User,
    load_relations: bool = False
) -> List[Spec_Room]:
    """
    Получить все типы помещений
    """
    await check_permission(current_user, "spec_room_read", "просмотра типов помещений")
    
    async with new_session() as session:
        return await spec_room_data.get_spec_room_all(session, load_relations=load_relations)

async def get_spec_room_options(
    current_user: User
) -> List[Spec_Room]:
    """
    Получить минимальную информацию о типах помещений для выпадающих списков
    """
    await check_permission(current_user, "spec_room_read", "просмотра типов помещений")
    
    async with new_session() as session:
        return await spec_room_data.get_spec_room_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_room_with_stats(
    spec_room_id: int,
    current_user: User
) -> dict:
    """
    Получить тип помещения со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "spec_room_read", "просмотра типов помещений")
    
    async with new_session() as session:
        # Получаем тип помещения (без загрузки связанных данных)
        spec_room = await spec_room_data.get_spec_room_by_id(
            session, 
            spec_room_id,
            load_relations=False
        )
        
        if not spec_room:
            raise HTTPException(
                status_code=404,
                detail=f"Тип помещения с id {spec_room_id} не найден"
            )
        
        # Получаем количество связанных объектов
        organizations_count = await spec_room_data.count_organizations_by_spec_room(session, spec_room_id)
        objects_count = await spec_room_data.count_objects_by_spec_room(session, spec_room_id)
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": spec_room.id,
            "name": spec_room.name,
            "organizations_count": organizations_count,
            "objects_count": objects_count
        }

async def get_spec_rooms_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список типов помещений со статистикой для ответа
    """
    await check_permission(current_user, "spec_room_read", "просмотра списка типов помещений")
    
    async with new_session() as session:
        # Получаем типы помещений (без загрузки связанных данных)
        items, total = await spec_room_data.get_spec_room_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=False
        )
        
        # Для каждого типа помещения получаем статистику
        result_items = []
        for item in items:
            organizations_count = await spec_room_data.count_organizations_by_spec_room(session, item.id)
            objects_count = await spec_room_data.count_objects_by_spec_room(session, item.id)
            
            result_items.append({
                "id": item.id,
                "name": item.name,
                "organizations_count": organizations_count,
                "objects_count": objects_count
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_room(
    spec_room_create: SpecRoomCreate,
    current_user: User
) -> Spec_Room:
    """
    Создать новый тип помещения
    """
    await check_permission(current_user, "spec_room_create", "создания типов помещений")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await spec_room_data.check_spec_room_name_exists(session, spec_room_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Тип помещения с названием '{spec_room_create.name}' уже существует"
            )
        
        # Создание
        spec_room = await spec_room_data.create_spec_room(session, spec_room_create)
        
        return spec_room

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_room(
    spec_room_id: int,
    spec_room_update: SpecRoomUpdate,
    current_user: User
) -> Spec_Room:
    """
    Обновить тип помещения
    """
    await check_permission(current_user, "spec_room_modify", "изменения типов помещений")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await spec_room_data.get_spec_room_by_id(session, spec_room_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип помещения с id {spec_room_id} не найден"
            )
        
        # Проверка уникальности названия, если оно меняется
        if spec_room_update.name and spec_room_update.name != existing.name:
            if await spec_room_data.check_spec_room_name_exists(session, spec_room_update.name, spec_room_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип помещения с названием '{spec_room_update.name}' уже существует"
                )
        
        # Обновление
        spec_room = await spec_room_data.update_spec_room(session, spec_room_id, spec_room_update)

        return spec_room

async def update_spec_room_with_stats(
    spec_room_id: int,
    spec_room_update: SpecRoomUpdate,
    current_user: User
) -> dict:
    """
    Обновить тип помещения и вернуть результат со статистикой (organizations_count, objects_count).
    Парный к get_spec_room_with_stats — чтобы api-слою не приходилось самому лазать в data.
    """
    # update_spec_room уже делает check_permission и валидации — не дублируем их
    spec_room = await update_spec_room(spec_room_id, spec_room_update, current_user)

    async with new_session() as session:
        organizations_count = await spec_room_data.count_organizations_by_spec_room(session, spec_room_id)
        objects_count = await spec_room_data.count_objects_by_spec_room(session, spec_room_id)

    return {
        "id": spec_room.id,
        "name": spec_room.name,
        "organizations_count": organizations_count,
        "objects_count": objects_count
    }

# ========== УДАЛЕНИЕ ==========

async def delete_spec_room(
    spec_room_id: int,
    current_user: User
) -> bool:
    """
    Удалить тип помещения
    """
    await check_permission(current_user, "spec_room_delete", "удаления типов помещений")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        spec_room = await spec_room_data.get_spec_room_by_id(
            session, 
            spec_room_id, 
            load_relations=True
        )
        
        if not spec_room:
            raise HTTPException(
                status_code=404,
                detail=f"Тип помещения с id {spec_room_id} не найден"
            )

        if spec_room.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_room.name}' — она необходима для работы системы."
            )

        # Проверка на наличие связанных организаций
        if spec_room.organizations and len(spec_room.organizations) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить тип помещения '{spec_room.name}': есть связанные организации ({len(spec_room.organizations)} шт.)"
            )
        
        # Проверка на наличие связанных объектов
        if spec_room.objects and len(spec_room.objects) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить тип помещения '{spec_room.name}': есть связанные объекты ({len(spec_room.objects)} шт.)"
            )
        
        # Удаление
        success = await spec_room_data.delete_spec_room(session, spec_room_id)
        
        return success