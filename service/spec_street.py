from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_street import Spec_Street
from data import spec_street as spec_street_data
from schema.spec_street import SpecStreetCreate, SpecStreetUpdate, SpecStreetResponse
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
        permission: Название права (spec_street_read, spec_street_create и т.д.)
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

async def get_spec_street_by_id(
                                spec_street_id: int,
                                current_user: User,
                                load_streets: bool = False
                                ) -> SpecStreetResponse:
    """
    Получить тип улицы по ID с проверкой прав
    """
    await check_permission(current_user, "spec_street_read", "просмотра типов улиц")
    
    async with new_session() as session:
        spec_street = await spec_street_data.get_spec_street_by_id(
                                                                    session, 
                                                                    spec_street_id, 
                                                                    load_streets=load_streets
                                                                    )
        
        if not spec_street:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип улицы с id {spec_street_id} не найден"
                                )
        
        return spec_street

async def get_spec_streets_paginated(
                                    pagination: PaginationParams,
                                    current_user: User,
                                    search: Optional[str] = None,
                                    sort_by: str = "name",
                                    sort_order: str = "asc"
                                    ) -> Tuple[List[Spec_Street], int]:
    """
    Получить список типов улиц с пагинацией
    """
    await check_permission(current_user, "spec_street_read", "просмотра списка типов улиц")
    
    async with new_session() as session:
        items, total = await spec_street_data.get_spec_street_paginated(
                                                                        session=session,
                                                                        skip=pagination.skip,
                                                                        limit=pagination.limit,
                                                                        search=search,
                                                                        sort_by=sort_by,
                                                                        sort_order=sort_order,
                                                                        load_streets=True  # Загружаем связанные улицы для подсчета
                                                                        )
        
        return items, total

async def get_all_spec_streets(
                                current_user: User,
                                load_streets: bool = False
                                ) -> List[Spec_Street]:
    """
    Получить все типы улиц
    """
    await check_permission(current_user, "spec_street_read", "просмотра типов улиц")
    
    async with new_session() as session:
        return await spec_street_data.get_spec_street_all(session, load_streets=load_streets)

async def get_spec_street_options(
                                    current_user: User
                                    ) -> List[Spec_Street]:
    """
    Получить минимальную информацию о типах улиц для выпадающих списков
    """
    await check_permission(current_user, "spec_street_read", "просмотра типов улиц")
    
    async with new_session() as session:
        return await spec_street_data.get_spec_street_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_street_with_stats(
                                    spec_street_id: int,
                                    current_user: User
                                    ) -> dict:
    """
    Получить тип улицы со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "spec_street_read", "просмотра типов улиц")
    
    async with new_session() as session:
        # Получаем тип улицы (без загрузки улиц)
        spec_street = await spec_street_data.get_spec_street_by_id(
                                                                    session, 
                                                                    spec_street_id,
                                                                    load_streets=False
                                                                    )
        
        if not spec_street:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип улицы с id {spec_street_id} не найден"
                                )
        
        # Получаем ТОЛЬКО количество связанных улиц
        streets_count = await spec_street_data.count_spec_street_streets(
                                                                        session, 
                                                                        spec_street_id
                                                                        )
        
        # Возвращаем готовый словарь для ответа
        return {
                "id": spec_street.id,
                "name": spec_street.name,
                "short_name": spec_street.short_name,
                "description": spec_street.description,
                "streets_count": streets_count
                }

async def get_spec_streets_paginated_with_stats(
                                                pagination: PaginationParams,
                                                current_user: User,
                                                search: Optional[str] = None,
                                                sort_by: str = "name",
                                                sort_order: str = "asc"
                                                ) -> Tuple[List[dict], int]:
    """
    Получить список типов улиц со статистикой для ответа
    """
    await check_permission(current_user, "spec_street_read", "просмотра списка типов улиц")
    
    async with new_session() as session:
        # Получаем типы улиц (без загрузки улиц)
        items, total = await spec_street_data.get_spec_street_paginated(
                                                                        session=session,
                                                                        skip=pagination.skip,
                                                                        limit=pagination.limit,
                                                                        search=search,
                                                                        sort_by=sort_by,
                                                                        sort_order=sort_order,
                                                                        load_streets=False
                                                                        )
        
        # Для каждого типа улицы получаем количество улиц
        result_items = []
        for item in items:
            streets_count = await spec_street_data.count_spec_street_streets(
                                                                            session, 
                                                                            item.id
                                                                            )
            result_items.append({
                                "id": item.id,
                                "name": item.name,
                                "short_name": item.short_name,
                                "description": item.description,
                                "streets_count": streets_count
                                })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_street(
                            spec_street_create: SpecStreetCreate,
                            current_user: User
                            ) -> Spec_Street:
    """
    Создать новый тип улицы
    """
    await check_permission(current_user, "spec_street_create", "создания типов улиц")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await spec_street_data.check_spec_street_name_exists(session, spec_street_create.name):
            raise HTTPException(
                                status_code=400,
                                detail=f"Тип улицы с названием '{spec_street_create.name}' уже существует"
                                )
        
        # Создание
        spec_street = await spec_street_data.create_spec_street(session, spec_street_create)
        
        return spec_street

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_street(
                            spec_street_id: int,
                            spec_street_update: SpecStreetUpdate,
                            current_user: User
                            ) -> Spec_Street:
    """
    Обновить тип улицы
    """
    await check_permission(current_user, "spec_street_modify", "изменения типов улиц")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await spec_street_data.get_spec_street_by_id(session, spec_street_id)
        if not existing:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип улицы с id {spec_street_id} не найден"
                                )
        
        # Проверка уникальности названия, если оно меняется
        if spec_street_update.name and spec_street_update.name != existing.name:
            if await spec_street_data.check_spec_street_name_exists(
                                                                    session,
                                                                    spec_street_update.name,
                                                                    spec_street_id
                                                                    ):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Тип улицы с названием '{spec_street_update.name}' уже существует"
                                    )
        
        # Обновление
        spec_street = await spec_street_data.update_spec_street(session, spec_street_id, spec_street_update)
        
        return spec_street

# ========== УДАЛЕНИЕ ==========

async def delete_spec_street(
                            spec_street_id: int,
                            current_user: User
                            ) -> bool:
    """
    Удалить тип улицы
    """
    await check_permission(current_user, "spec_street_delete", "удаления типов улиц")
    
    async with new_session() as session:
        # Проверяем существование и связанные улицы
        spec_street = await spec_street_data.get_spec_street_by_id(
                                                                    session, 
                                                                    spec_street_id, 
                                                                    load_streets=True
                                                                    )
        
        if not spec_street:
            raise HTTPException(
                                    status_code=404,
                                    detail=f"Тип улицы с id {spec_street_id} не найден"
                                )

        if spec_street.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_street.name}' — она необходима для работы системы."
            )

        # Проверка на наличие связанных улиц
        if spec_street.streets and len(spec_street.streets) > 0:
            raise HTTPException(
                                    status_code=400,
                                    detail=f"Невозможно удалить тип улицы '{spec_street.name}': \
                                    есть связанные улицы ({len(spec_street.streets)} шт.)"
                                )
        
        # Удаление
        success = await spec_street_data.delete_spec_street(session, spec_street_id)
        
        return success