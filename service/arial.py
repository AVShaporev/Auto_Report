from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.arial import Arial
from data import arial as arial_data
from data import spec_arial as spec_arial_data
from schema.arial import ArialCreate, ArialUpdate
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
        permission: Название права (arial_read, arial_create и т.д.)
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

async def get_arial_by_id(
    arial_id: int,
    current_user: User,
    load_relations: bool = False
) -> Arial:
    """
    Получить район по ID с проверкой прав
    """
    await check_permission(current_user, "arial_read", "просмотра районов")
    
    async with new_session() as session:
        arial = await arial_data.get_by_id(
            session, 
            arial_id, 
            load_relations=load_relations
        )
        
        if not arial:
            raise HTTPException(
                status_code=404,
                detail=f"Район с id {arial_id} не найден"
            )
        
        return arial

async def get_arials_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_arial_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Arial], int]:
    """
    Получить список районов с пагинацией
    """
    await check_permission(current_user, "arial_read", "просмотра списка районов")
    
    async with new_session() as session:
        items, total = await arial_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_arial_id=spec_arial_id,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True  # Загружаем связанные данные для ответа
        )
        
        return items, total

async def get_all_arials(
    current_user: User,
    load_relations: bool = False
) -> List[Arial]:
    """
    Получить все районы
    """
    await check_permission(current_user, "arial_read", "просмотра районов")
    
    async with new_session() as session:
        return await arial_data.get_all(session, load_relations=load_relations)

async def get_arial_options(
    current_user: User
) -> List[Arial]:
    """
    Получить минимальную информацию о районах для выпадающих списков
    """
    await check_permission(current_user, "arial_read", "просмотра районов")
    
    async with new_session() as session:
        return await arial_data.get_options(session)

async def get_arial_options_by_spec(
    spec_arial_id: int,
    current_user: User
) -> List[Arial]:
    """
    Получить минимальную информацию о районах для выпадающих списков по типу
    """
    await check_permission(current_user, "arial_read", "просмотра районов")
    
    async with new_session() as session:
        # Проверяем существование типа района
        if not await spec_arial_data.check_name_exists(session, spec_arial_id):
            raise HTTPException(
                status_code=404,
                detail=f"Тип района с id {spec_arial_id} не найден"
            )
        
        return await arial_data.get_options_by_spec_arial(session, spec_arial_id)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_arial_with_stats(
    arial_id: int,
    current_user: User
) -> dict:
    """
    Получить район со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "arial_read", "просмотра районов")
    
    async with new_session() as session:
        # Получаем район с загрузкой типа района
        arial = await arial_data.get_by_id(
            session, 
            arial_id,
            load_relations=True
        )
        
        if not arial:
            raise HTTPException(
                status_code=404,
                detail=f"Район с id {arial_id} не найден"
            )
        
        # Получаем количество связанных объектов
        organizations_count = await arial_data.count_organizations(session, arial_id)
        objects_count = await arial_data.count_objects(session, arial_id)
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": arial.id,
            "name": arial.name,
            "spec_arial_id": arial.spec_arial_id,
            "spec_arial_name": arial.spec_arial.name if arial.spec_arial else None,
            "organizations_count": organizations_count,
            "objects_count": objects_count
        }

async def get_arials_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_arial_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список районов со статистикой для ответа
    """
    await check_permission(current_user, "arial_read", "просмотра списка районов")
    
    async with new_session() as session:
        # Получаем районы с загрузкой типа района
        items, total = await arial_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_arial_id=spec_arial_id,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )
        
        # Для каждого района получаем статистику
        result_items = []
        for item in items:
            organizations_count = await arial_data.count_organizations(session, item.id)
            objects_count = await arial_data.count_objects(session, item.id)
            
            result_items.append({
                "id": item.id,
                "name": item.name,
                "spec_arial_name": item.spec_arial.name if item.spec_arial else None,
                "organizations_count": organizations_count,
                "objects_count": objects_count
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_arial(
    arial_create: ArialCreate,
    current_user: User
) -> Arial:
    """
    Создать новый район
    """
    await check_permission(current_user, "arial_create", "создания районов")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await arial_data.check_name_exists(session, arial_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Район с названием '{arial_create.name}' уже существует"
            )
        
        # Проверка существования типа района
        if not await arial_data.check_spec_arial_exists(session, arial_create.spec_arial_id):
            raise HTTPException(
                status_code=400,
                detail=f"Тип района с id {arial_create.spec_arial_id} не существует"
            )
        
        # Создание
        arial = await arial_data.create(session, arial_create)
        
        return arial

# ========== ОБНОВЛЕНИЕ ==========

async def update_arial(
    arial_id: int,
    arial_update: ArialUpdate,
    current_user: User
) -> Arial:
    """
    Обновить район
    """
    await check_permission(current_user, "arial_modify", "изменения районов")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await arial_data.get_by_id(session, arial_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Район с id {arial_id} не найден"
            )
        
        # Проверка уникальности названия, если оно меняется
        if arial_update.name and arial_update.name != existing.name:
            if await arial_data.check_name_exists(session, arial_update.name, arial_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Район с названием '{arial_update.name}' уже существует"
                )
        
        # Проверка существования типа района, если он меняется
        if arial_update.spec_arial_id and arial_update.spec_arial_id != existing.spec_arial_id:
            if not await arial_data.check_spec_arial_exists(session, arial_update.spec_arial_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип района с id {arial_update.spec_arial_id} не существует"
                )
        
        # Обновление
        arial = await arial_data.update(session, arial_id, arial_update)
        
        return arial

# ========== УДАЛЕНИЕ ==========

async def delete_arial(
    arial_id: int,
    current_user: User
) -> bool:
    """
    Удалить район
    """
    await check_permission(current_user, "arial_delete", "удаления районов")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        arial = await arial_data.get_by_id(
            session, 
            arial_id, 
            load_relations=True
        )
        
        if not arial:
            raise HTTPException(
                status_code=404,
                detail=f"Район с id {arial_id} не найден"
            )
        
        # Проверка на наличие связанных организаций
        if arial.organizations and len(arial.organizations) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить район '{arial.name}': есть связанные организации ({len(arial.organizations)} шт.)"
            )
        
        # Проверка на наличие связанных объектов
        if arial.objects and len(arial.objects) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить район '{arial.name}': есть связанные объекты ({len(arial.objects)} шт.)"
            )
        
        # Удаление
        success = await arial_data.delete(session, arial_id)
        
        return success