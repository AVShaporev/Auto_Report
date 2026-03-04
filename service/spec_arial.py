from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_arial import Spec_Arial
from data import spec_arial as spec_arial_data
from schema.spec_arial import SpecArialCreate, SpecArialUpdate
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
        permission: Название права (spec_arial_read, spec_arial_create и т.д.)
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

async def get_spec_arial_by_id(
    spec_arial_id: int,
    current_user: User,
    load_arials: bool = False
) -> Spec_Arial:
    """
    Получить тип района по ID с проверкой прав
    """
    await check_permission(current_user, "spec_arial_read", "просмотра типов районов")
    
    async with new_session() as session:
        spec_arial = await spec_arial_data.get_by_id(
            session, 
            spec_arial_id, 
            load_arials=load_arials
        )
        
        if not spec_arial:
            raise HTTPException(
                status_code=404,
                detail=f"Тип района с id {spec_arial_id} не найден"
            )
        
        return spec_arial

async def get_spec_arials_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Spec_Arial], int]:
    """
    Получить список типов районов с пагинацией
    """
    await check_permission(current_user, "spec_arial_read", "просмотра списка типов районов")
    
    async with new_session() as session:
        items, total = await spec_arial_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_arials=True  # Загружаем связанные районы для подсчета
        )
        
        return items, total

async def get_all_spec_arials(
    current_user: User,
    load_arials: bool = False
) -> List[Spec_Arial]:
    """
    Получить все типы районов
    """
    await check_permission(current_user, "spec_arial_read", "просмотра типов районов")
    
    async with new_session() as session:
        return await spec_arial_data.get_all(session, load_arials=load_arials)

async def get_spec_arial_options(
    current_user: User
) -> List[Spec_Arial]:
    """
    Получить минимальную информацию о типах районов для выпадающих списков
    """
    await check_permission(current_user, "spec_arial_read", "просмотра типов районов")
    
    async with new_session() as session:
        return await spec_arial_data.get_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_arial_with_stats(
    spec_arial_id: int,
    current_user: User
) -> dict:
    """
    Получить тип района со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "spec_arial_read", "просмотра типов районов")
    
    async with new_session() as session:
        # Получаем тип района (без загрузки районов)
        spec_arial = await spec_arial_data.get_by_id(
            session, 
            spec_arial_id,
            load_arials=False
        )
        
        if not spec_arial:
            raise HTTPException(
                status_code=404,
                detail=f"Тип района с id {spec_arial_id} не найден"
            )
        
        # Получаем ТОЛЬКО количество связанных районов
        arials_count = await spec_arial_data.count_arials(
            session, 
            spec_arial_id
        )
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": spec_arial.id,
            "name": spec_arial.name,
            "arials_count": arials_count
        }

async def get_spec_arials_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список типов районов со статистикой для ответа
    """
    await check_permission(current_user, "spec_arial_read", "просмотра списка типов районов")
    
    async with new_session() as session:
        # Получаем типы районов (без загрузки районов)
        items, total = await spec_arial_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_arials=False
        )
        
        # Для каждого типа района получаем количество районов
        result_items = []
        for item in items:
            arials_count = await spec_arial_data.count_arials(
                session, 
                item.id
            )
            result_items.append({
                "id": item.id,
                "name": item.name,
                "arials_count": arials_count
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_arial(
    spec_arial_create: SpecArialCreate,
    current_user: User
) -> Spec_Arial:
    """
    Создать новый тип района
    """
    await check_permission(current_user, "spec_arial_create", "создания типов районов")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await spec_arial_data.check_name_exists(session, spec_arial_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Тип района с названием '{spec_arial_create.name}' уже существует"
            )
        
        # Создание
        spec_arial = await spec_arial_data.create(session, spec_arial_create)
        
        return spec_arial

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_arial(
    spec_arial_id: int,
    spec_arial_update: SpecArialUpdate,
    current_user: User
) -> Spec_Arial:
    """
    Обновить тип района
    """
    await check_permission(current_user, "spec_arial_modify", "изменения типов районов")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await spec_arial_data.get_by_id(session, spec_arial_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип района с id {spec_arial_id} не найден"
            )
        
        # Проверка уникальности названия, если оно меняется
        if spec_arial_update.name and spec_arial_update.name != existing.name:
            if await spec_arial_data.check_name_exists(session, spec_arial_update.name, spec_arial_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип района с названием '{spec_arial_update.name}' уже существует"
                )
        
        # Обновление
        spec_arial = await spec_arial_data.update(session, spec_arial_id, spec_arial_update)
        
        return spec_arial

# ========== УДАЛЕНИЕ ==========

async def delete_spec_arial(
    spec_arial_id: int,
    current_user: User
) -> bool:
    """
    Удалить тип района
    """
    await check_permission(current_user, "spec_arial_delete", "удаления типов районов")
    
    async with new_session() as session:
        # Проверяем существование и связанные районы
        spec_arial = await spec_arial_data.get_by_id(
            session, 
            spec_arial_id, 
            load_arials=True
        )
        
        if not spec_arial:
            raise HTTPException(
                status_code=404,
                detail=f"Тип района с id {spec_arial_id} не найден"
            )
        
        # Проверка на наличие связанных районов
        if spec_arial.arials and len(spec_arial.arials) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить тип района '{spec_arial.name}': есть связанные районы ({len(spec_arial.arials)} шт.)"
            )
        
        # Удаление
        success = await spec_arial_data.delete(session, spec_arial_id)
        
        return success