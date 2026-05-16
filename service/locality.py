from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.locality import Locality
from data import locality as locality_data
from data import spec_locality as spec_locality_data
from schema.locality import LocalityCreate, LocalityUpdate
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
        permission: Название права (locality_read, locality_create и т.д.)
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

async def get_locality_by_id(
                                locality_id: int,
                                current_user: User,
                                load_relations: bool = False
                                ) -> Locality:
    """
    Получить населенный пункт по ID с проверкой прав
    """
    await check_permission(current_user, "locality_read", "просмотра населенных пунктов")
    
    async with new_session() as session:
        locality = await locality_data.get_locality_by_id(
                                                            session, 
                                                            locality_id, 
                                                            load_relations=load_relations
                                                            )
        
        if not locality:
            raise HTTPException(
                                status_code=404,
                                detail=f"Населенный пункт с id {locality_id} не найден"
                                )
        
        return locality

async def get_localities_paginated(
                                    pagination: PaginationParams,
                                    current_user: User,
                                    search: Optional[str] = None,
                                    spec_locality_id: Optional[int] = None,
                                    sort_by: str = "name",
                                    sort_order: str = "asc"
                                    ) -> Tuple[List[Locality], int]:
    """
    Получить список населенных пунктов с пагинацией
    """
    await check_permission(current_user, "locality_read", "просмотра списка населенных пунктов")
    
    async with new_session() as session:
        items, total = await locality_data.get_locality_paginated(
                                                                    session=session,
                                                                    skip=pagination.skip,
                                                                    limit=pagination.limit,
                                                                    search=search,
                                                                    spec_locality_id=spec_locality_id,
                                                                    sort_by=sort_by,
                                                                    sort_order=sort_order,
                                                                    load_relations=True  # Загружаем связанные данные для ответа
                                                                    )
        
        return items, total

async def get_all_localities(
                            current_user: User,
                            load_relations: bool = False
                            ) -> List[Locality]:
    """
    Получить все населенные пункты
    """
    await check_permission(current_user, "locality_read", "просмотра населенных пунктов")
    
    async with new_session() as session:
        return await locality_data.get_locality_all(session, load_relations=load_relations)

async def get_locality_options(
                                current_user: User
                                ) -> List[Locality]:
    """
    Получить минимальную информацию о населенных пунктах для выпадающих списков
    """
    await check_permission(current_user, "locality_read", "просмотра населенных пунктов")
    
    async with new_session() as session:
        return await locality_data.get_locality_options(session)

async def get_locality_options_by_spec(
                                        spec_locality_id: int,
                                        current_user: User
                                        ) -> List[Locality]:
    """
    Получить минимальную информацию о населенных пунктах для выпадающих списков по типу
    """
    await check_permission(current_user, "locality_read", "просмотра населенных пунктов")
    
    async with new_session() as session:
        # Проверяем существование типа населенного пункта
        if not await spec_locality_data.get_spec_locality_by_id(session, spec_locality_id):
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип населенного пункта с id {spec_locality_id} не найден"
                                )
        
        return await locality_data.get_locality_options_by_spec_locality(session, spec_locality_id)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_locality_with_stats(
                                    locality_id: int,
                                    current_user: User
                                    ) -> dict:
    """
    Получить населенный пункт со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "locality_read", "просмотра населенных пунктов")
    
    async with new_session() as session:
        # Получаем населенный пункт с загрузкой типа
        locality = await locality_data.get_locality_by_id(
                                                            session, 
                                                            locality_id,
                                                            load_relations=True
                                                            )
        
        if not locality:
            raise HTTPException(
                                status_code=404,
                                detail=f"Населенный пункт с id {locality_id} не найден"
                                )
        
        # Получаем количество связанных объектов
        organizations_count = await locality_data.count_locality_organizations(session, locality_id)
        objects_count = await locality_data.count_locality_objects(session, locality_id)
        
        # Возвращаем готовый словарь для ответа
        return {
                "id": locality.id,
                "name": locality.name,
                "spec_locality_id": locality.spec_locality_id,
                "spec_locality_name": locality.spec_locality.name if locality.spec_locality else None,
                "spec_locality_short_name": locality.spec_locality.short_name if locality.spec_locality else None,
                "organizations_count": organizations_count,
                "objects_count": objects_count
                }

async def get_localities_paginated_with_stats(
                                                pagination: PaginationParams,
                                                current_user: User,
                                                search: Optional[str] = None,
                                                spec_locality_id: Optional[int] = None,
                                                sort_by: str = "name",
                                                sort_order: str = "asc"
                                                ) -> Tuple[List[dict], int]:
    """
    Получить список населенных пунктов со статистикой для ответа
    """
    await check_permission(current_user, "locality_read", "просмотра списка населенных пунктов")
    
    async with new_session() as session:
        # Получаем населенные пункты с загрузкой типа
        items, total = await locality_data.get_locality_paginated(
                                                                    session=session,
                                                                    skip=pagination.skip,
                                                                    limit=pagination.limit,
                                                                    search=search,
                                                                    spec_locality_id=spec_locality_id,
                                                                    sort_by=sort_by,
                                                                    sort_order=sort_order,
                                                                    load_relations=True
                                                                    )
        
        # Для каждого населенного пункта получаем статистику
        result_items = []
        for item in items:
            organizations_count = await locality_data.count_locality_organizations(session, item.id)
            objects_count = await locality_data.count_locality_objects(session, item.id)
            
            result_items.append({
                                "id": item.id,
                                "name": item.name,
                                "spec_locality_name": item.spec_locality.name if item.spec_locality else None,
                                "organizations_count": organizations_count,
                                "objects_count": objects_count
                                })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_locality(
                            locality_create: LocalityCreate,
                            current_user: User
                            ) -> Locality:
    """
    Создать новый населенный пункт
    """
    await check_permission(current_user, "locality_create", "создания населенных пунктов")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await locality_data.check_locality_name_exists(session, locality_create.name):
            raise HTTPException(
                                status_code=400,
                                detail=f"Населенный пункт с названием '{locality_create.name}' уже существует"
                                )
        
        # Проверка существования типа населенного пункта (если указан)
        if locality_create.spec_locality_id:
            if not await locality_data.check_locality_spec_locality_exists(
                                                                            session,
                                                                            locality_create.spec_locality_id):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Тип населенного пункта с id \
                                    {locality_create.spec_locality_id} не существует"
                                    )
        
        # Создание
        locality = await locality_data.create_locality(session, locality_create)
        
        return locality

# ========== ОБНОВЛЕНИЕ ==========

async def update_locality(
                            locality_id: int,
                            locality_update: LocalityUpdate,
                            current_user: User
                            ) -> Locality:
    """
    Обновить населенный пункт
    """
    await check_permission(current_user, "locality_modify", "изменения населенных пунктов")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await locality_data.get_locality_by_id(session, locality_id)
        if not existing:
            raise HTTPException(
                                status_code=404,
                                detail=f"Населенный пункт с id {locality_id} не найден"
                                )
        
        # Проверка уникальности названия, если оно меняется
        if locality_update.name and locality_update.name != existing.name:
            if await locality_data.check_locality_name_exists(session, locality_update.name, locality_id):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Населенный пункт с названием \
                                    '{locality_update.name}' уже существует"
                                    )
        
        # Проверка существования типа населенного пункта, если он меняется
        if locality_update.spec_locality_id and locality_update.spec_locality_id != existing.spec_locality_id:
            if not await locality_data.check_locality_spec_locality_exists(
                                                                            session,
                                                                            locality_update.spec_locality_id
                                                                            ):
                raise HTTPException(
                                        status_code=400,
                                        detail=f"Тип населенного пункта с id \
                                        {locality_update.spec_locality_id} не существует"
                                    )
        
        # Обновление
        locality = await locality_data.update_locality(session, locality_id, locality_update)
        
        return locality

# ========== УДАЛЕНИЕ ==========

async def delete_locality(
                            locality_id: int,
                            current_user: User
                            ) -> bool:
    """
    Удалить населенный пункт
    """
    await check_permission(current_user, "locality_delete", "удаления населенных пунктов")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        locality = await locality_data.get_locality_by_id(
                                                            session, 
                                                            locality_id, 
                                                            load_relations=True
                                                            )
        
        if not locality:
            raise HTTPException(
                                status_code=404,
                                detail=f"Населенный пункт с id {locality_id} не найден"
                                )
        
        # Проверка на наличие связанных организаций
        if locality.organizations and len(locality.organizations) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить населенный пункт \
                                '{locality.name}': есть связанные организации \
                                ({len(locality.organizations)} шт.)"
                                )
        
        # Проверка на наличие связанных объектов
        if locality.objects and len(locality.objects) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить населенный пункт \
                                '{locality.name}': есть связанные объекты \
                                ({len(locality.objects)} шт.)"
                                )
        
        # Удаление
        success = await locality_data.delete_locality(session, locality_id)
        
        return success