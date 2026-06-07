from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_locality import Spec_Locality
from data import spec_locality as spec_locality_data
from schema.spec_locality import SpecLocalityCreate, SpecLocalityUpdate
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
        permission: Название права (spec_locality_read, spec_locality_create и т.д.)
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

async def get_spec_locality_by_id(
    spec_locality_id: int,
    current_user: User,
    load_localities: bool = False
) -> Spec_Locality:
    """
    Получить тип населенного пункта по ID с проверкой прав
    """
    await check_permission(current_user, "spec_locality_read", "просмотра типов населенных пунктов")
    
    async with new_session() as session:
        spec_locality = await spec_locality_data.get_spec_locality_by_id(
            session, 
            spec_locality_id, 
            load_localities=load_localities
        )
        
        if not spec_locality:
            raise HTTPException(
                status_code=404,
                detail=f"Тип населенного пункта с id {spec_locality_id} не найден"
            )
        
        return spec_locality

async def get_spec_localities_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Spec_Locality], int]:
    """
    Получить список типов населенных пунктов с пагинацией
    """
    await check_permission(current_user, "spec_locality_read", "просмотра списка типов населенных пунктов")
    
    async with new_session() as session:
        items, total = await spec_locality_data.get_spec_locality_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_localities=True  # Загружаем связанные населенные пункты для подсчета
        )
        
        return items, total

async def get_all_spec_localities(
    current_user: User,
    load_localities: bool = False
) -> List[Spec_Locality]:
    """
    Получить все типы населенных пунктов
    """
    await check_permission(current_user, "spec_locality_read", "просмотра типов населенных пунктов")
    
    async with new_session() as session:
        return await spec_locality_data.get_spec_locality_all(session, load_localities=load_localities)

async def get_spec_locality_options(
    current_user: User
) -> List[Spec_Locality]:
    """
    Получить минимальную информацию о типах населенных пунктов для выпадающих списков
    """
    await check_permission(current_user, "spec_locality_read", "просмотра типов населенных пунктов")
    
    async with new_session() as session:
        return await spec_locality_data.get_spec_locality_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_locality_with_stats(
    spec_locality_id: int,
    current_user: User
) -> dict:
    """
    Получить тип населенного пункта со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "spec_locality_read", "просмотра типов населенных пунктов")
    
    async with new_session() as session:
        # Получаем тип населенного пункта (без загрузки населенных пунктов)
        spec_locality = await spec_locality_data.get_spec_locality_by_id(
            session, 
            spec_locality_id,
            load_localities=False
        )
        
        if not spec_locality:
            raise HTTPException(
                status_code=404,
                detail=f"Тип населенного пункта с id {spec_locality_id} не найден"
            )
        
        # Получаем ТОЛЬКО количество связанных населенных пунктов
        localities_count = await spec_locality_data.count_localities_by_spec_locality(
            session, 
            spec_locality_id
        )
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": spec_locality.id,
            "name": spec_locality.name,
            "short_name": spec_locality.short_name,
            "localities_count": localities_count
        }

async def get_spec_localities_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список типов населенных пунктов со статистикой для ответа
    """
    await check_permission(current_user, "spec_locality_read", "просмотра списка типов населенных пунктов")
    
    async with new_session() as session:
        # Получаем типы населенных пунктов (без загрузки населенных пунктов)
        items, total = await spec_locality_data.get_spec_locality_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_localities=False
        )
        
        # Для каждого типа получаем количество населенных пунктов
        result_items = []
        for item in items:
            localities_count = await spec_locality_data.count_localities_by_spec_locality(
                session, 
                item.id
            )
            result_items.append({
                "id": item.id,
                "name": item.name,
                "short_name": item.short_name,
                "localities_count": localities_count
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_locality(
    spec_locality_create: SpecLocalityCreate,
    current_user: User
) -> Spec_Locality:
    """
    Создать новый тип населенного пункта
    """
    await check_permission(current_user, "spec_locality_create", "создания типов населенных пунктов")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await spec_locality_data.check_spec_locality_name_exists(session, spec_locality_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Тип населенного пункта с названием '{spec_locality_create.name}' уже существует"
            )
        
        # Создание
        spec_locality = await spec_locality_data.create_spec_locality(session, spec_locality_create)
        
        return spec_locality

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_locality(
    spec_locality_id: int,
    spec_locality_update: SpecLocalityUpdate,
    current_user: User
) -> Spec_Locality:
    """
    Обновить тип населенного пункта
    """
    await check_permission(current_user, "spec_locality_modify", "изменения типов населенных пунктов")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await spec_locality_data.get_spec_locality_by_id(session, spec_locality_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип населенного пункта с id {spec_locality_id} не найден"
            )
        
        # Проверка уникальности названия, если оно меняется
        if spec_locality_update.name and spec_locality_update.name != existing.name:
            if await spec_locality_data.check_spec_locality_name_exists(session, spec_locality_update.name, spec_locality_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип населенного пункта с названием '{spec_locality_update.name}' уже существует"
                )
        
        # Обновление
        spec_locality = await spec_locality_data.update_spec_locality(session, spec_locality_id, spec_locality_update)
        
        return spec_locality

# ========== УДАЛЕНИЕ ==========

async def delete_spec_locality(
    spec_locality_id: int,
    current_user: User
) -> bool:
    """
    Удалить тип населенного пункта
    """
    await check_permission(current_user, "spec_locality_delete", "удаления типов населенных пунктов")
    
    async with new_session() as session:
        # Проверяем существование и связанные населенные пункты
        spec_locality = await spec_locality_data.get_spec_locality_by_id(
            session, 
            spec_locality_id, 
            load_localities=True
        )
        
        if not spec_locality:
            raise HTTPException(
                status_code=404,
                detail=f"Тип населенного пункта с id {spec_locality_id} не найден"
            )

        if spec_locality.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_locality.name}' — она необходима для работы системы."
            )

        # Проверка на наличие связанных населенных пунктов
        if spec_locality.localitys and len(spec_locality.localitys) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить тип населенного пункта '{spec_locality.name}': есть связанные населенные пункты ({len(spec_locality.localitys)} шт.)"
            )
        
        # Удаление
        success = await spec_locality_data.delete_spec_locality(session, spec_locality_id)
        
        return success