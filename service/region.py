from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.region import Region
from data import region as region_data
from data import spec_region as spec_region_data
from schema.region import RegionCreate, RegionUpdate
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
        permission: Название права (region_read, region_create и т.д.)
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

async def get_region_by_id(
                            region_id: int,
                            current_user: User,
                            load_relations: bool = False
                            ) -> Region:
    """
    Получить регион по ID с проверкой прав
    """
    await check_permission(current_user, "region_read", "просмотра регионов")
    
    async with new_session() as session:
        region = await region_data.get_region_by_id(
                                                    session, 
                                                    region_id, 
                                                    load_relations=load_relations
                                                    )
        
        if not region:
            raise HTTPException(
                                status_code=404,
                                detail=f"Регион с id {region_id} не найден"
                                )

        return region

async def get_regions_paginated(
                                pagination: PaginationParams,
                                current_user: User,
                                search: Optional[str] = None,
                                spec_region_id: Optional[int] = None,
                                sort_by: str = "name",
                                sort_order: str = "asc"
                                ) -> Tuple[List[Region], int]:
    """
    Получить список регионов с пагинацией
    """
    await check_permission(current_user, "region_read", "просмотра списка регионов")
    
    async with new_session() as session:
        items, total = await region_data.get_region_paginated(
                                                        session=session,
                                                        skip=pagination.skip,
                                                        limit=pagination.limit,
                                                        search=search,
                                                        spec_region_id=spec_region_id,
                                                        sort_by=sort_by,
                                                        sort_order=sort_order,
                                                        load_relations=True  # Загружаем связанные данные для ответа
                                                        )
        
        return items, total

async def get_all_regions(
                        current_user: User
                        ) -> List[dict]:
    """
    Получить все регионы
    """
    await check_permission(current_user, "region_read", "просмотра регионов")
    
    async with new_session() as session:
        # Получаем регионы с загрузкой только spec_купшщт
        regions = await region_data.get_region_all(
                                                    session,
                                                    load_relations=True
                                                    )
        # Получаем словари с количеством организаций и объектов
        org_counts = await region_data.get_organizations_count_by_region(session)
        obj_counts = await region_data.get_objects_count_by_region(session)

    result = []
    for region in regions:
        result.append({
            "id": region.id,
            "name": region.name,
            "symbol": region.symbol,
            "spec_arial_name": region.spec_region.name if region.spec_region else None,
            "organizations_count": org_counts.get(region.id, 0),
            "objects_count": obj_counts.get(region.id, 0)
        })
    return result

async def get_region_options(
                            current_user: User
                            ) -> List[Region]:
    """
    Получить минимальную информацию о регионах для выпадающих списков
    """
    await check_permission(current_user, "region_read", "просмотра регионов")
    
    async with new_session() as session:
        return await region_data.get_region_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_region_with_stats(
                                region_id: int,
                                current_user: User
                                ) -> dict:
    """
    Получить регион со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "region_read", "просмотра регионов")
    
    async with new_session() as session:
        # Получаем регион с загрузкой типа региона
        region = await region_data.get_region_by_id(
                                            session, 
                                            region_id,
                                            load_relations=True
                                            )
        
        if not region:
            raise HTTPException(
                                status_code=404,
                                detail=f"Регион с id {region_id} не найден"
                                )
        
        # Получаем количество связанных объектов
        organizations_count = await region_data.count_region_organizations(session, region_id)
        objects_count = await region_data.count_region_objects(session, region_id)
        
        # Возвращаем готовый словарь для ответа
        return {
                "id": region.id,
                "name": region.name,
                "symbol": region.symbol,
                "spec_region_id": region.spec_region_id,
                "spec_region_name": region.spec_region.name if region.spec_region else None,
                "organizations_count": organizations_count,
                "objects_count": objects_count
                }

async def get_regions_paginated_with_stats(
                                            pagination: PaginationParams,
                                            current_user: User,
                                            search: Optional[str] = None,
                                            spec_region_id: Optional[int] = None,
                                            sort_by: str = "name",
                                            sort_order: str = "asc"
                                            ) -> Tuple[List[dict], int]:
    """
    Получить список регионов со статистикой для ответа
    """
    await check_permission(current_user, "region_read", "просмотра списка регионов")
    
    async with new_session() as session:
        # Получаем регионы с загрузкой типа региона
        items, total = await region_data.get_region_paginated(
                                                            session=session,
                                                            skip=pagination.skip,
                                                            limit=pagination.limit,
                                                            search=search,
                                                            spec_region_id=spec_region_id,
                                                            sort_by=sort_by,
                                                            sort_order=sort_order,
                                                            load_relations=True
                                                            )
        
        # Для каждого региона получаем статистику
        result_items = []
        for item in items:
            organizations_count = await region_data.count_region_organizations(session, item.id)
            objects_count = await region_data.count_region_objects(session, item.id)
            
            result_items.append({
                                "id": item.id,
                                "name": item.name,
                                "symbol": item.symbol,
                                "spec_region_name": item.spec_region.name if item.spec_region else None,
                                "organizations_count": organizations_count,
                                "objects_count": objects_count
                                })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_region(
                        region_create: RegionCreate,
                        current_user: User
                        ) -> Region:
    """
    Создать новый регион
    """
    await check_permission(current_user, "region_create", "создания регионов")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await region_data.check_region_name_exists(session, region_create.name):
            raise HTTPException(
                                status_code=400,
                                detail=f"Регион с названием '{region_create.name}' уже существует"
                                )
        
        # Проверка уникальности символа
        if await region_data.check_region_symbol_exists(session, region_create.symbol):
            raise HTTPException(
                                status_code=400,
                                detail=f"Регион с символом '{region_create.symbol}' уже существует"
                                )
        
        # Проверка существования типа региона
        if not await region_data.check_region_spec_region_exists(
                                                                session, 
                                                                region_create.spec_region_id
                                                                ):
            raise HTTPException(
                                status_code=400,
                                detail=f"Тип региона с id {region_create.spec_region_id} не существует"
                                )
                            
        # Создание
        region = await region_data.create_region(session, region_create)
        
        return region

# ========== ОБНОВЛЕНИЕ ==========

async def update_region(
                        region_id: int,
                        region_update: RegionUpdate,
                        current_user: User
                        ) -> Region:
    """
    Обновить регион
    """
    await check_permission(current_user, "region_modify", "изменения регионов")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await region_data.get_region_by_id(session, region_id)
        if not existing:
            raise HTTPException(
                                status_code=404,
                                detail=f"Регион с id {region_id} не найден"
                                )
        
        # Проверка уникальности названия, если оно меняется
        if region_update.name and region_update.name != existing.name:
            if await region_data.check_region_name_exists(session, region_update.name, region_id):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Регион с названием '{region_update.name}' уже существует"
                                    )
        
        # Проверка уникальности символа, если он меняется
        if region_update.symbol and region_update.symbol != existing.symbol:
            if await region_data.check_region_symbol_exists(session, region_update.symbol, region_id):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Регион с символом '{region_update.symbol}' уже существует"
                                    )
        
        # Проверка существования типа региона, если он меняется
        if region_update.spec_region_id and region_update.spec_region_id != existing.spec_region_id:
            if not await region_data.check_region_spec_region_exists(session, region_update.spec_region_id):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Тип региона с id {region_update.spec_region_id} не существует"
                                    )
        
        # Обновление
        region = await region_data.update_region(session, region_id, region_update)
        
        return region

# ========== УДАЛЕНИЕ ==========

async def delete_region(
                        region_id: int,
                        current_user: User
                        ) -> bool:
    """
    Удалить регион
    """
    await check_permission(current_user, "region_delete", "удаления регионов")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        region = await region_data.get_region_by_id(
                                            session,
                                            region_id,
                                            load_relations=True
                                            )
        
        if not region:
            raise HTTPException(
                                status_code=404,
                                detail=f"Регион с id {region_id} не найден"
                                )
        
        # Проверка на наличие связанных организаций
        if region.organizations and len(region.organizations) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить регион '{region.name}': \
                                есть связанные организации ({len(region.organizations)} шт.)"
                                )
        
        # Проверка на наличие связанных объектов
        if region.objects and len(region.objects) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить регион '{region.name}': \
                                есть связанные объекты ({len(region.objects)} шт.)"
                                )
        
        # Удаление
        success = await region_data.delete_region(session, region_id)
        
        return success