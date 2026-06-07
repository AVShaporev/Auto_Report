from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_build import Spec_Build
from data import spec_build as spec_build_data
from schema.spec_build import SpecBuildCreate, SpecBuildUpdate
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
        permission: Название права (spec_build_read, spec_build_create и т.д.)
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

async def get_spec_build_by_id(
                                spec_build_id: int,
                                current_user: User,
                                load_relations: bool = False
                                ) -> Spec_Build:
    """
    Получить тип строения по ID с проверкой прав
    """
    await check_permission(current_user, "spec_build_read", "просмотра типов строений")
    
    async with new_session() as session:
        spec_build = await spec_build_data.get_spec_build_by_id(
                                                                session, 
                                                                spec_build_id, 
                                                                load_relations=load_relations
                                                                )
        
        if not spec_build:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип строения с id {spec_build_id} не найден"
                                )
        
        return spec_build

async def get_spec_builds_paginated(
                                        pagination: PaginationParams,
                                        current_user: User,
                                        search: Optional[str] = None,
                                        sort_by: str = "name",
                                        sort_order: str = "asc"
                                    ) -> Tuple[List[Spec_Build], int]:
    """
    Получить список типов строений с пагинацией
    """
    await check_permission(current_user, "spec_build_read", "просмотра списка типов строений")
    
    async with new_session() as session:
        items, total = await spec_build_data.get_spec_build_paginated(
                                                                        session=session,
                                                                        skip=pagination.skip,
                                                                        limit=pagination.limit,
                                                                        search=search,
                                                                        sort_by=sort_by,
                                                                        sort_order=sort_order,
                                                                        load_relations=True  # Загружаем связанные данные для подсчета
                                                                        )
        
        return items, total

async def get_all_spec_builds(
                                current_user: User,
                                load_relations: bool = False
                                ) -> List[Spec_Build]:
    """
    Получить все типы строений
    """
    await check_permission(current_user, "spec_build_read", "просмотра типов строений")
    
    async with new_session() as session:
        return await spec_build_data.get_spec_build_all(session, load_relations=load_relations)

async def get_spec_build_options(
                                current_user: User
                                ) -> List[Spec_Build]:
    """
    Получить минимальную информацию о типах строений для выпадающих списков
    """
    await check_permission(current_user, "spec_build_read", "просмотра типов строений")
    
    async with new_session() as session:
        return await spec_build_data.get_spec_build_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_build_with_stats(
                                    spec_build_id: int,
                                    current_user: User
                                    ) -> dict:
    """
    Получить тип строения со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "spec_build_read", "просмотра типов строений")
    
    async with new_session() as session:
        # Получаем тип строения (без загрузки связанных данных)
        spec_build = await spec_build_data.get_spec_build_by_id(
                                                                session, 
                                                                spec_build_id,
                                                                load_relations=False
                                                                )
        
        if not spec_build:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип строения с id {spec_build_id} не найден"
                                )
        
        # Получаем количество связанных объектов
        organizations_count = await spec_build_data.count_spec_build_organizations(session, spec_build_id)
        objects_count = await spec_build_data.count_spec_build_objects(session, spec_build_id)
        
        # Возвращаем готовый словарь для ответа
        return {
                "id": spec_build.id,
                "name": spec_build.name,
                "organizations_count": organizations_count,
                "objects_count": objects_count
                }

async def get_spec_builds_paginated_with_stats(
                                                pagination: PaginationParams,
                                                current_user: User,
                                                search: Optional[str] = None,
                                                sort_by: str = "name",
                                                sort_order: str = "asc"
                                                ) -> Tuple[List[dict], int]:
    """
    Получить список типов строений со статистикой для ответа
    """
    await check_permission(current_user, "spec_build_read", "просмотра списка типов строений")
    
    async with new_session() as session:
        # Получаем типы строений (без загрузки связанных данных)
        items, total = await spec_build_data.get_spec_build_paginated(
                                                                        session=session,
                                                                        skip=pagination.skip,
                                                                        limit=pagination.limit,
                                                                        search=search,
                                                                        sort_by=sort_by,
                                                                        sort_order=sort_order,
                                                                        load_relations=False
                                                                        )
        
        # Для каждого типа строения получаем статистику
        result_items = []
        for item in items:
            organizations_count = await spec_build_data.count_spec_build_organizations(session, item.id)
            objects_count = await spec_build_data.count_spec_build_objects(session, item.id)
            
            result_items.append({
                                "id": item.id,
                                "name": item.name,
                                "organizations_count": organizations_count,
                                "objects_count": objects_count
                                })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_build(
                            spec_build_create: SpecBuildCreate,
                            current_user: User
                            ) -> Spec_Build:
    """
    Создать новый тип строения
    """
    await check_permission(current_user, "spec_build_create", "создания типов строений")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await spec_build_data.check_spec_build_name_exists(session, spec_build_create.name):
            raise HTTPException(
                                status_code=400,
                                detail=f"Тип строения с названием '{spec_build_create.name}' уже существует"
                                )
        
        # Создание
        spec_build = await spec_build_data.create_spec_build(session, spec_build_create)
        
        return spec_build

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_build(
                            spec_build_id: int,
                            spec_build_update: SpecBuildUpdate,
                            current_user: User
                            ) -> Spec_Build:
    """
    Обновить тип строения
    """
    await check_permission(current_user, "spec_build_modify", "изменения типов строений")

    async with new_session() as session:
        # Проверяем существование
        existing = await spec_build_data.get_spec_build_by_id(session, spec_build_id)
        if not existing:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип строения с id {spec_build_id} не найден"
                                )

        # Проверка уникальности названия, если оно меняется
        if spec_build_update.name and spec_build_update.name != existing.name:
            if await spec_build_data.check_spec_build_name_exists(
                                                                    session,
                                                                    spec_build_update.name,
                                                                    spec_build_id
                                                                    ):
                raise HTTPException(
                                    status_code=400,
                                    detail=f"Тип строения с названием \
                                    '{spec_build_update.name}' уже существует"
                                    )

        # Обновление
        spec_build = await spec_build_data.update_spec_build(session, spec_build_id, spec_build_update)

        return spec_build

async def update_spec_build_with_stats(
                                        spec_build_id: int,
                                        spec_build_update: SpecBuildUpdate,
                                        current_user: User
                                        ) -> dict:
    """
    Обновить тип строения и вернуть результат со статистикой (organizations_count, objects_count).
    Парный к get_spec_build_with_stats — чтобы api-слою не приходилось самому лазать в data.
    """
    # update_spec_build уже делает check_permission и валидации — не дублируем их
    spec_build = await update_spec_build(spec_build_id, spec_build_update, current_user)

    async with new_session() as session:
        organizations_count = await spec_build_data.count_spec_build_organizations(session, spec_build_id)
        objects_count = await spec_build_data.count_spec_build_objects(session, spec_build_id)

    return {
            "id": spec_build.id,
            "name": spec_build.name,
            "organizations_count": organizations_count,
            "objects_count": objects_count
            }

# ========== УДАЛЕНИЕ ==========

async def delete_spec_build(
                            spec_build_id: int,
                            current_user: User
                            ) -> bool:
    """
    Удалить тип строения
    """
    await check_permission(current_user, "spec_build_delete", "удаления типов строений")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        spec_build = await spec_build_data.get_spec_build_by_id(
                                                                session, 
                                                                spec_build_id, 
                                                                load_relations=True
                                                                )
        
        if not spec_build:
            raise HTTPException(
                                status_code=404,
                                detail=f"Тип строения с id {spec_build_id} не найден"
                                )

        if spec_build.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_build.name}' — она необходима для работы системы."
            )

        # Проверка на наличие связанных организаций
        if spec_build.organizations and len(spec_build.organizations) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить тип строения \
                                '{spec_build.name}': есть связанные организации \
                                в количестве - ({len(spec_build.organizations)} шт.)"
                                )
        
        # Проверка на наличие связанных объектов
        if spec_build.objects and len(spec_build.objects) > 0:
            raise HTTPException(
                                status_code=400,
                                detail=f"Невозможно удалить тип строения \
                                '{spec_build.name}': есть связанные объекты \
                                в количестве({len(spec_build.objects)} шт.)"
                                )
        
        # Удаление
        success = await spec_build_data.delete_spec_build(session, spec_build_id)
        
        return success