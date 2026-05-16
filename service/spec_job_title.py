from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_job_title import Spec_Job_Title
from data import spec_job_title as spec_job_title_data
from schema.spec_job_title import SpecJobTitleCreate, SpecJobTitleUpdate
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
        permission: Название права (spec_job_title_read, spec_job_title_create и т.д.)
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

async def get_spec_job_title_by_id(
                                    spec_job_title_id: int,
                                    current_user: User,
                                    load_organizations: bool = False
                                    ) -> Spec_Job_Title:
    """
    Получить должность руководителя по ID с проверкой прав
    """
    await check_permission(current_user, "spec_job_title_read", "просмотра должностей руководителей")
    
    async with new_session() as session:
        spec_job_title = await spec_job_title_data.get_spec_job_title_by_id(
                                                            session, 
                                                            spec_job_title_id, 
                                                            load_organizations=load_organizations
                                                            )
        
        if not spec_job_title:
            raise HTTPException(
                                status_code=404,
                                detail=f"Должность руководителя с id {spec_job_title_id} не найдена"
                                )

        if not load_organizations and hasattr(spec_job_title, 'organizations'):
            delattr(spec_job_title, 'organizations')
        
        return spec_job_title

async def get_spec_job_titles_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Spec_Job_Title], int]:
    """
    Получить список должностей руководителей с пагинацией
    """
    await check_permission(current_user, "spec_job_title_read", "просмотра списка должностей")
    
    async with new_session() as session:
        items, total = await spec_job_title_data.get_spec_job_title_paginated(
                                                                session=session,
                                                                skip=pagination.skip,
                                                                limit=pagination.limit,
                                                                search=search,
                                                                sort_by=sort_by,
                                                                sort_order=sort_order,
                                                                load_organizations=True  # Загружаем организации для подсчета
                                                                )
                                                                
        return items, total

async def get_all_spec_job_titles(
                                    current_user: User,
                                    load_organizations: bool = False
                                ) -> List[Spec_Job_Title]:
    """
    Получить все должности руководителей
    """
    await check_permission(current_user, "spec_job_title_read", "просмотра должностей")
    
    async with new_session() as session:
        return await spec_job_title_data.get_spec_job_title_all(session, load_organizations=load_organizations)

# ========== СОЗДАНИЕ ==========

async def create_spec_job_title(
    spec_job_title_create: SpecJobTitleCreate,
    current_user: User
) -> Spec_Job_Title:
    """
    Создать новую должность руководителя
    """
    await check_permission(current_user, "spec_job_title_create", "создания должностей")
    
    async with new_session() as session:
        # Проверка уникальности названия
        exists = await spec_job_title_data.check_spec_job_title_name_exists(
            session, 
            spec_job_title_create.name
        )
        if exists:
            raise HTTPException(
                status_code=400,
                detail=f"Должность с названием '{spec_job_title_create.name}' уже существует"
            )
        
        # Создание
        spec_job_title = await spec_job_title_data.create_spec_job_title(session, spec_job_title_create)
        
        return spec_job_title

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_job_title(
                                spec_job_title_id: int,
                                spec_job_title_update: SpecJobTitleUpdate,
                                current_user: User, 
                                load_organizations: bool = True
                                ) -> Spec_Job_Title:
    """
    Обновить должность руководителя
    """
    await check_permission(current_user, "spec_job_title_modify", "изменения должностей")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await spec_job_title_data.get_spec_job_title_by_id(session, spec_job_title_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Должность с id {spec_job_title_id} не найдена"
            )
        
        # Проверка уникальности названия, если оно меняется
        if spec_job_title_update.name and spec_job_title_update.name != existing.name:
            exists = await spec_job_title_data.check_spec_job_title_name_exists(
                session, 
                spec_job_title_update.name, 
                spec_job_title_id
            )
            if exists:
                raise HTTPException(
                    status_code=400,
                    detail=f"Должность с названием '{spec_job_title_update.name}' уже существует"
                )
        
        # Обновление
        spec_job_title = await spec_job_title_data.update_spec_job_title(
            session, 
            spec_job_title_id, 
            spec_job_title_update
        )

        if not load_organizations and hasattr(spec_job_title, 'organizations'):
            delattr(spec_job_title, 'organizations')
        
        return spec_job_title

# ========== УДАЛЕНИЕ ==========

async def delete_spec_job_title(
    spec_job_title_id: int,
    current_user: User
) -> bool:
    """
    Удалить должность руководителя
    """
    await check_permission(current_user, "spec_job_title_delete", "удаления должностей")
    
    async with new_session() as session:
        # Проверяем существование и связанные организации
        spec_job_title = await spec_job_title_data.get_spec_job_title_by_id(
            session, 
            spec_job_title_id, 
            load_organizations=True
        )
        
        if not spec_job_title:
            raise HTTPException(
                status_code=404,
                detail=f"Должность с id {spec_job_title_id} не найдена"
            )
        
        # Проверка на наличие связанных организаций
        if spec_job_title.organizations and len(spec_job_title.organizations) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить должность '{spec_job_title.name}': есть связанные организации ({len(spec_job_title.organizations)} шт.)"
            )
        
        # Удаление
        success = await spec_job_title_data.delete_spec_job_title(session, spec_job_title_id)
        
        return success

async def get_spec_job_title_with_stats(
    spec_job_title_id: int,
    current_user: User
) -> dict:
    """
    Получить должность руководителя со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "spec_job_title_read", "просмотра должностей")
    
    async with new_session() as session:
        # Получаем саму должность (без загрузки организаций)
        spec_job_title = await spec_job_title_data.get_spec_job_title_by_id(
            session, 
            spec_job_title_id,
            load_organizations=False  # Не загружаем организации!
        )
        
        if not spec_job_title:
            raise HTTPException(
                status_code=404,
                detail=f"Должность с id {spec_job_title_id} не найдена"
            )
        
        # Получаем ТОЛЬКО количество связанных организаций
        organizations_count = await spec_job_title_data.count_organizations_by_spec_job_title(
            session, 
            spec_job_title_id
        )
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": spec_job_title.id,
            "name": spec_job_title.name,
            "organizations_count": organizations_count
        }

async def update_spec_job_title_with_stats(
    spec_job_title_id: int,
    spec_job_title_update: SpecJobTitleUpdate,
    current_user: User
) -> dict:
    """
    Обновить должность руководителя и вернуть готовый словарь со статистикой.
    """
    await check_permission(current_user, "spec_job_title_modify", "изменения должностей")

    async with new_session() as session:
        existing = await spec_job_title_data.get_spec_job_title_by_id(session, spec_job_title_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Должность с id {spec_job_title_id} не найдена"
            )

        if spec_job_title_update.name and spec_job_title_update.name != existing.name:
            exists = await spec_job_title_data.check_spec_job_title_name_exists(
                session,
                spec_job_title_update.name,
                spec_job_title_id
            )
            if exists:
                raise HTTPException(
                    status_code=400,
                    detail=f"Должность с названием '{spec_job_title_update.name}' уже существует"
                )

        spec_job_title = await spec_job_title_data.update_spec_job_title(
            session,
            spec_job_title_id,
            spec_job_title_update
        )

        organizations_count = await spec_job_title_data.count_organizations_by_spec_job_title(
            session,
            spec_job_title_id
        )

        return {
            "id": spec_job_title.id,
            "name": spec_job_title.name,
            "organizations_count": organizations_count
        }

async def get_spec_job_titles_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список должностей со статистикой для ответа
    """
    await check_permission(current_user, "spec_job_title_read", "просмотра списка")
    
    async with new_session() as session:
        # Получаем сами должности (без загрузки организаций)
        items, total = await spec_job_title_data.get_spec_job_title_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_organizations=False  # Не загружаем организации!
        )
        
        # Для каждой должности получаем количество организаций
        result_items = []
        for item in items:
            organizations_count = await spec_job_title_data.count_organizations_by_spec_job_title(
                session, 
                item.id
            )
            result_items.append({
                "id": item.id,
                "name": item.name,
                "organizations_count": organizations_count
            })
        
        return result_items, total