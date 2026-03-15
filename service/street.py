from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.street import Street
from data import street as street_data
from data import spec_street as spec_street_data
from schema.street import StreetCreate, StreetUpdate
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
        permission: Название права (street_read, street_create и т.д.)
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

async def get_street_by_id(
                            street_id: int,
                            current_user: User,
                            load_relations: bool = False
                            ) -> Street:
    """
    Получить улицу по ID с проверкой прав
    """
    await check_permission(current_user, "street_read", "просмотра улиц")
    
    async with new_session() as session:
        street = await street_data.get_street_by_id(
                                                    session, 
                                                    street_id, 
                                                    load_relations=load_relations
                                                    )
        
        if not street:
            raise HTTPException(
                                status_code=404,
                                detail=f"Улица с id {street_id} не найдена"
                                )
        
        return street

async def get_streets_paginated(
                                pagination: PaginationParams,
                                current_user: User,
                                search: Optional[str] = None,
                                spec_street_id: Optional[int] = None,
                                sort_by: str = "name",
                                sort_order: str = "asc"
                                ) -> Tuple[List[Street], int]:
    """
    Получить список улиц с пагинацией
    """
    await check_permission(current_user, "street_read", "просмотра списка улиц")
    
    async with new_session() as session:
        items, total = await street_data.get_street_paginated(
                                                                session=session,
                                                                skip=pagination.skip,
                                                                limit=pagination.limit,
                                                                search=search,
                                                                spec_street_id=spec_street_id,
                                                                sort_by=sort_by,
                                                                sort_order=sort_order,
                                                                load_relations=True  # Загружаем связанные данные для ответа
                                                                )
        
        return items, total

async def get_all_streets(
                            current_user: User,
                            load_relations: bool = False
                            ) -> List[Street]:
    """
    Получить все улицы
    """
    await check_permission(current_user, "street_read", "просмотра улиц")
    
    async with new_session() as session:
        return await street_data.get_street_all(session, load_relations=load_relations)

async def get_street_options(
                            current_user: User
                            ) -> List[Street]:
    """
    Получить минимальную информацию об улицах для выпадающих списков
    """
    await check_permission(current_user, "street_read", "просмотра улиц")
    
    async with new_session() as session:
        return await street_data.get_street_options(session)

async def get_street_options_by_spec(
                                    spec_street_id: int,
                                    current_user: User
                                    ) -> List[Street]:
    """
    Получить минимальную информацию об улицах для выпадающих списков по типу
    """
    await check_permission(current_user, "street_read", "просмотра улиц")
    
    async with new_session() as session:
        # Проверяем существование типа улицы
        if not await spec_street_data.check_street_name_exists(session, spec_street_id):
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип улицы с id {spec_street_id} не найден"
                                )
        
        return await street_data.get_street_options_by_spec_street(session, spec_street_id)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_street_with_stats(
                                street_id: int,
                                current_user: User
                                ) -> dict:
    """
    Получить улицу со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "street_read", "просмотра улиц")
    
    async with new_session() as session:
        # Получаем улицу с загрузкой типа
        street = await street_data.get_street_by_id(
                                                    session, 
                                                    street_id,
                                                    load_relations=True
                                                    )
        
        if not street:
            raise HTTPException(
                                status_code=404,
                                detail=f"Улица с id {street_id} не найдена"
                                )
        
        # Получаем количество связанных объектов
        organizations_count = await street_data.count_street_organizations(session, street_id)
        objects_count = await street_data.count_street_objects(session, street_id)
        
        # Возвращаем готовый словарь для ответа
        return {
                    "id": street.id,
                    "name": street.name,
                    "spec_street_id": street.spec_street_id,
                    "spec_street_name": street.spec_street.name if street.spec_street else None,
                    "organizations_count": organizations_count,
                    "objects_count": objects_count
                }

async def get_streets_paginated_with_stats(
                                            pagination: PaginationParams,
                                            current_user: User,
                                            search: Optional[str] = None,
                                            spec_street_id: Optional[int] = None,
                                            sort_by: str = "name",
                                            sort_order: str = "asc"
                                            ) -> Tuple[List[dict], int]:
    """
    Получить список улиц со статистикой для ответа
    """
    await check_permission(current_user, "street_read", "просмотра списка улиц")
    
    async with new_session() as session:
        # Получаем улицы с загрузкой типа
        items, total = await street_data.get_street_paginated(
                                                                session=session,
                                                                skip=pagination.skip,
                                                                limit=pagination.limit,
                                                                search=search,
                                                                spec_street_id=spec_street_id,
                                                                sort_by=sort_by,
                                                                sort_order=sort_order,
                                                                load_relations=True
                                                                )
        
        # Для каждой улицы получаем статистику
        result_items = []
        for item in items:
            organizations_count = await street_data.count_street_organizations(session, item.id)
            objects_count = await street_data.count_street_objects(session, item.id)
            
            result_items.append({
                                "id": item.id,
                                "name": item.name,
                                "spec_street_name": item.spec_street.name if item.spec_street else None,
                                "organizations_count": organizations_count,
                                "objects_count": objects_count
                                })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_street(
                        street_create: StreetCreate,
                        current_user: User
                        ) -> Street:
    """
    Создать новую улицу
    """
    await check_permission(current_user, "street_create", "создания улиц")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await street_data.check_street_name_exists(session, street_create.name):
            raise HTTPException(
                                status_code=400,
                                detail=f"Улица с названием '{street_create.name}' уже существует"
                                )
        
        # Проверка существования типа улицы
        if not await street_data.check_street_spec_street_exists(session, street_create.spec_street_id):
            raise HTTPException(
                                status_code=400,
                                detail=f"Тип улицы с id {street_create.spec_street_id} не существует"
                                )
        
        # Создание
        street = await street_data.create_street(session, street_create)
        
        return street

# ========== ОБНОВЛЕНИЕ ==========

async def update_street(
                        street_id: int,
                        street_update: StreetUpdate,
                        current_user: User
                        ) -> Street:
    """
    Обновить улицу
    """
    await check_permission(current_user, "street_modify", "изменения улиц")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await street_data.get_street_by_id(session, street_id)
        if not existing:
            raise HTTPException(
                                status_code=404,
                                detail=f"Улица с id {street_id} не найдена"
                                )
        
        # Проверка уникальности названия, если оно меняется
        if street_update.name and street_update.name != existing.name:
            if await street_data.check_street_name_exists(session, street_update.name, street_id):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Улица с названием '{street_update.name}' уже существует"
                                    )
        
        # Проверка существования типа улицы, если он меняется
        if street_update.spec_street_id and street_update.spec_street_id != existing.spec_street_id:
            if not await street_data.check_street_spec_street_exists(session, street_update.spec_street_id):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Тип улицы с id {street_update.spec_street_id} не существует"
                                    )
        
        # Обновление
        street = await street_data.update_street(session, street_id, street_update)
        
        return street

# ========== УДАЛЕНИЕ ==========

async def delete_street(
                        street_id: int,
                        current_user: User
                        ) -> bool:
    """
    Удалить улицу
    """
    await check_permission(current_user, "street_delete", "удаления улиц")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        street = await street_data.get_street_by_id(
                                                    session, 
                                                    street_id, 
                                                    load_relations=True
                                                    )
        
        if not street:
            raise HTTPException(
                                status_code=404,
                                detail=f"Улица с id {street_id} не найдена"
                                )
        
        # Проверка на наличие связанных организаций
        if street.organizations and len(street.organizations) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить улицу '{street.name}': есть связанные организации ({len(street.organizations)} шт.)"
                                )
        
        # Проверка на наличие связанных объектов
        if street.objects and len(street.objects) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить улицу '{street.name}': есть связанные объекты ({len(street.objects)} шт.)"
                                )
        
        # Удаление
        success = await street_data.delete_street(session, street_id)
        
        return success