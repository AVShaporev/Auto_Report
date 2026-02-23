from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.organization import Organization
from data import organization as org_data
from schema.organization import OrganizationCreate, OrganizationUpdate
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
        permission: Название права (organization_read, organization_modify и т.д.)
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

async def get_organization_by_id(
    org_id: int,
    current_user: User,
    load_relations: bool = True
) -> Optional[Organization]:
    """
    Получить организацию по ID с проверкой прав
    """
    # Проверка права на чтение
    await check_permission(current_user, "organization_read", "просмотра организаций")
    
    async with new_session() as session:
        organization = await org_data.get_by_id(session, org_id, load_relations)
        
        if not organization:
            raise HTTPException(
                status_code=404,
                detail=f"Организация с id {org_id} не найдена"
            )
        
        return organization

async def get_organizations_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    customer: Optional[bool] = None,
    executor: Optional[bool] = None,
    region_id: Optional[int] = None,
    bank_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Organization], int]:
    """
    Получить список организаций с пагинацией и проверкой прав
    """
    # Проверка права на чтение
    await check_permission(current_user, "organization_read", "просмотра списка организаций")
    
    async with new_session() as session:
        organizations, total = await org_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            customer=customer,
            executor=executor,
            region_id=region_id,
            bank_id=bank_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return organizations, total

async def get_all_organizations(
    current_user: User,
    load_relations: bool = False
) -> List[Organization]:
    """
    Получить все организации (без пагинации)
    """
    await check_permission(current_user, "organization_read", "просмотра организаций")
    
    async with new_session() as session:
        return await org_data.get_all(session, load_relations)

# ========== СОЗДАНИЕ ==========

async def create_organization(
    org_create: OrganizationCreate,
    current_user: User
) -> Organization:
    """
    Создать новую организацию с проверкой прав
    """
    # Проверка права на создание
    await check_permission(current_user, "organization_create", "создания организаций")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await org_data.check_name_exists(session, org_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Организация с названием '{org_create.name}' уже существует"
            )
        
        # Проверка уникальности сокращенного названия
        if await org_data.check_short_name_exists(session, org_create.short_name):
            raise HTTPException(
                status_code=400,
                detail=f"Организация с сокращенным названием '{org_create.short_name}' уже существует"
            )
        
        # Проверка уникальности ИНН
        if await org_data.check_inn_exists(session, org_create.inn):
            raise HTTPException(
                status_code=400,
                detail=f"Организация с ИНН '{org_create.inn}' уже существует"
            )
        
        # Создание организации
        organization = await org_data.create(session, org_create)
        
        # Загружаем связанные данные для ответа
        organization = await org_data.get_by_id(session, organization.id, load_relations=True)
        
        return organization

# ========== ОБНОВЛЕНИЕ ==========

async def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    current_user: User
) -> Organization:
    """
    Обновить организацию с проверкой прав
    """
    # Проверка права на изменение
    await check_permission(current_user, "organization_modify", "изменения организаций")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await org_data.get_by_id(session, org_id, load_relations=False)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Организация с id {org_id} не найдена"
            )
        
        # Проверка уникальности названия, если оно меняется
        if org_update.name and org_update.name != existing.name:
            if await org_data.check_name_exists(session, org_update.name, org_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Организация с названием '{org_update.name}' уже существует"
                )
        
        # Проверка уникальности сокращенного названия
        if org_update.short_name and org_update.short_name != existing.short_name:
            if await org_data.check_short_name_exists(session, org_update.short_name, org_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Организация с сокращенным названием '{org_update.short_name}' уже существует"
                )
        
        # Проверка уникальности ИНН
        if org_update.inn and org_update.inn != existing.inn:
            if await org_data.check_inn_exists(session, org_update.inn, org_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Организация с ИНН '{org_update.inn}' уже существует"
                )
        
        # Обновление
        organization = await org_data.update(session, org_id, org_update)
        
        # Загружаем связанные данные
        organization = await org_data.get_by_id(session, org_id, load_relations=True)
        
        return organization

# ========== УДАЛЕНИЕ ==========

async def delete_organization(
    org_id: int,
    current_user: User
) -> bool:
    """
    Удалить организацию с проверкой прав
    """
    # Проверка права на удаление
    await check_permission(current_user, "organization_delete", "удаления организаций")
    
    async with new_session() as session:
        # Проверяем существование
        organization = await org_data.get_by_id(session, org_id, load_relations=False)
        if not organization:
            raise HTTPException(
                status_code=404,
                detail=f"Организация с id {org_id} не найдена"
            )
        
        # Здесь можно добавить проверку на наличие связанных объектов
        # (например, контрактов, отчетов и т.д.)
        
        # Удаление
        success = await org_data.delete(session, org_id)
        
        return success