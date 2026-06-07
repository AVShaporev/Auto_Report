from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_region import Spec_Region
from data import spec_region as spec_region_data
from schema.spec_region import SpecRegionCreate, SpecRegionUpdate
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
        permission: Название права (spec_region_read, spec_region_create и т.д.)
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

async def get_spec_region_by_id(
                                spec_region_id: int,
                                current_user: User,
                                load_regions: bool = False
                                ) -> Spec_Region:
    """
    Получить тип региона по ID с проверкой прав
    """
    await check_permission(current_user, "spec_region_read", "просмотра типов регионов")
    
    async with new_session() as session:
        spec_region = await spec_region_data.get_spec_region_by_id(
                                                                    session, 
                                                                    spec_region_id, 
                                                                    load_regions=load_regions
                                                                    )
        
        if not spec_region:
            raise HTTPException(
                                    status_code=404,
                                    detail=f"Тип региона с id {spec_region_id} не найден"
                                )
        
        return spec_region

async def get_spec_regions_paginated(
                                    pagination: PaginationParams,
                                    current_user: User,
                                    search: Optional[str] = None,
                                    sort_by: str = "name",
                                    sort_order: str = "asc"
                                    ) -> Tuple[List[Spec_Region], int]:
    """
    Получить список типов регионов с пагинацией
    """
    await check_permission(current_user, "spec_region_read", "просмотра списка типов регионов")
    
    async with new_session() as session:
        items, total = await spec_region_data.get_spec_region_paginated(
                                                                        session=session,
                                                                        skip=pagination.skip,
                                                                        limit=pagination.limit,
                                                                        search=search,
                                                                        sort_by=sort_by,
                                                                        sort_order=sort_order,
                                                                        load_regions=True  # Загружаем связанные регионы для подсчета
                                                                        )
        
        return items, total

async def get_all_spec_regions(
                                current_user: User,
                                load_regions: bool = False
                                ) -> List[Spec_Region]:
    """
    Получить все типы регионов
    """
    await check_permission(current_user, "spec_region_read", "просмотра типов регионов")
    
    async with new_session() as session:
        return await spec_region_data.get_spec_region_all(session, load_regions=load_regions)

async def get_spec_region_options(
                                    current_user: User
                                    ) -> List[Spec_Region]:
    """
    Получить минимальную информацию о типах регионов для выпадающих списков
    """
    await check_permission(current_user, "spec_region_read", "просмотра типов регионов")
    
    async with new_session() as session:
        return await spec_region_data.get_spec_region_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_region_with_stats(
                                    spec_region_id: int,
                                    current_user: User
                                    ) -> dict:
    """
    Получить тип региона со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "spec_region_read", "просмотра типов регионов")
    
    async with new_session() as session:
        # Получаем тип региона (без загрузки регионов)
        spec_region = await spec_region_data.get_spec_region_by_id(
                                                                    session, 
                                                                    spec_region_id,
                                                                    load_regions=False
                                                                    )
        
        if not spec_region:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип региона с id {spec_region_id} не найден"
                                )
        
        # Получаем ТОЛЬКО количество связанных регионов
        regions_count = await spec_region_data.count_spec_region_regions(
                                                                        session, 
                                                                        spec_region_id
                                                                        )
        
        # Возвращаем готовый словарь для ответа
        return {
                "id": spec_region.id,
                "is_system": spec_region.is_system,
                "name": spec_region.name,
                "description": spec_region.description,
                "regions_count": regions_count
                }

async def get_spec_regions_paginated_with_stats(
                                                pagination: PaginationParams,
                                                current_user: User,
                                                search: Optional[str] = None,
                                                sort_by: str = "name",
                                                sort_order: str = "asc"
                                                ) -> Tuple[List[dict], int]:
    """
    Получить список типов регионов со статистикой для ответа
    """
    await check_permission(current_user, "spec_region_read", "просмотра списка типов регионов")
    
    async with new_session() as session:
        # Получаем типы регионов (без загрузки регионов)
        items, total = await spec_region_data.get_spec_region_paginated(
                                                                        session=session,
                                                                        skip=pagination.skip,
                                                                        limit=pagination.limit,
                                                                        search=search,
                                                                        sort_by=sort_by,
                                                                        sort_order=sort_order,
                                                                        load_regions=False
                                                                        )
                    
        # Для каждого типа региона получаем количество регионов
        result_items = []
        for item in items:
            regions_count = await spec_region_data.count_spec_region_regions(
                                                                            session, 
                                                                            item.id
                                                                            )
            result_items.append({
                                "id": item.id,
                                "is_system": item.is_system,
                                "name": item.name,
                                "description": item.description if item.description else "",
                                "regions_count": regions_count
                                })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_region(
                            spec_region_create: SpecRegionCreate,
                            current_user: User
                            ) -> Spec_Region:
    """
    Создать новый тип региона
    """
    await check_permission(current_user, "spec_region_create", "создания типов регионов")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await spec_region_data.check_spec_region_name_exists(session, spec_region_create.name):
            raise HTTPException(
                                status_code=400,
                                detail=f"Тип региона с названием '{spec_region_create.name}' уже существует"
                                )
        
        # Создание
        spec_region = await spec_region_data.create_spec_region(session, spec_region_create)
        
        return spec_region

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_region(
                            spec_region_id: int,
                            spec_region_update: SpecRegionUpdate,
                            current_user: User
                            ) -> Spec_Region:
    """
    Обновить тип региона
    """
    await check_permission(current_user, "spec_region_modify", "изменения типов регионов")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await spec_region_data.get_spec_region_by_id(session, spec_region_id)
        if not existing:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип региона с id {spec_region_id} не найден"
                                )
        
        # Проверка уникальности названия, если оно меняется
        if spec_region_update.name and spec_region_update.name != existing.name:
            if await spec_region_data.check_spec_region_name_exists(
                                                                    session,
                                                                    spec_region_update.name,
                                                                    spec_region_id
                                                                    ):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Тип региона с названием '{spec_region_update.name}' уже существует"
                                    )
        
        # Обновление
        spec_region = await spec_region_data.update_spec_region(
                                                                session,
                                                                spec_region_id,
                                                                spec_region_update)
        
        return spec_region

# ========== УДАЛЕНИЕ ==========

async def delete_spec_region(
                            spec_region_id: int,
                            current_user: User
                            ) -> bool:
    """
    Удалить тип региона
    """
    await check_permission(current_user, "spec_region_delete", "удаления типов регионов")
    
    async with new_session() as session:
        # Проверяем существование и связанные регионы
        spec_region = await spec_region_data.get_spec_region_by_id(
                                                                    session, 
                                                                    spec_region_id, 
                                                                    load_regions=True
                                                                    )
        
        if not spec_region:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип региона с id {spec_region_id} не найден"
                                )

        if spec_region.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_region.name}' — она необходима для работы системы."
            )

        # Проверка на наличие связанных регионов
        if spec_region.regions and len(spec_region.regions) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить тип региона '{spec_region.name}': есть связанные регионы ({len(spec_region.regions)} шт.)"
                                )
        
        # Удаление
        success = await spec_region_data.delete_spec_region(session, spec_region_id)
        
        return success