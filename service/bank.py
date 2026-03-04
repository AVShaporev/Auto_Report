from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.bank import Bank
from data import bank as bank_data
from schema.bank import BankCreate, BankUpdate
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
        permission: Название права (bank_read, bank_create и т.д.)
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

async def get_bank_by_id(
    bank_id: int,
    current_user: User,
    load_organizations: bool = False
) -> Bank:
    """
    Получить банк по ID с проверкой прав
    """
    await check_permission(current_user, "bank_read", "просмотра банков")
    
    async with new_session() as session:
        bank = await bank_data.get_by_id(
            session, 
            bank_id, 
            load_organizations=load_organizations
        )
        
        if not bank:
            raise HTTPException(
                status_code=404,
                detail=f"Банк с id {bank_id} не найден"
            )
        
        return bank

async def get_banks_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Bank], int]:
    """
    Получить список банков с пагинацией
    """
    await check_permission(current_user, "bank_read", "просмотра списка банков")
    
    async with new_session() as session:
        items, total = await bank_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_organizations=True  # Загружаем организации для подсчета
        )
        
        return items, total

async def get_all_banks(
    current_user: User,
    load_organizations: bool = False
) -> List[Bank]:
    """
    Получить все банки
    """
    await check_permission(current_user, "bank_read", "просмотра банков")
    
    async with new_session() as session:
        return await bank_data.get_all(session, load_organizations=load_organizations)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_bank_with_stats(
    bank_id: int,
    current_user: User
) -> dict:
    """
    Получить банк со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "bank_read", "просмотра банков")
    
    async with new_session() as session:
        # Получаем сам банк (без загрузки организаций)
        bank = await bank_data.get_by_id(
            session, 
            bank_id,
            load_organizations=False
        )
        
        if not bank:
            raise HTTPException(
                status_code=404,
                detail=f"Банк с id {bank_id} не найден"
            )
        
        # Получаем ТОЛЬКО количество связанных организаций
        organizations_count = await bank_data.count_organizations(
            session, 
            bank_id
        )
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": bank.id,
            "name": bank.name,
            "bik": bank.bik,
            "inn": bank.inn,
            "organizations_count": organizations_count
        }

async def get_banks_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список банков со статистикой для ответа
    """
    await check_permission(current_user, "bank_read", "просмотра списка банков")
    
    async with new_session() as session:
        # Получаем сами банки (без загрузки организаций)
        items, total = await bank_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_organizations=False
        )
        
        # Для каждого банка получаем количество организаций
        result_items = []
        for item in items:
            organizations_count = await bank_data.count_organizations(
                                                                        session, 
                                                                        item.id
                                                                        )
            result_items.append({
                                "id": item.id,
                                "name": item.name,
                                "bik": item.bik,
                                "inn": item.inn,
                                "organizations_count": organizations_count
                                })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_bank(
    bank_create: BankCreate,
    current_user: User
) -> Bank:
    """
    Создать новый банк
    """
    await check_permission(current_user, "bank_create", "создания банков")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await bank_data.check_name_exists(session, bank_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Банк с названием '{bank_create.name}' уже существует"
            )
        
        # Проверка уникальности БИК
        if await bank_data.check_bik_exists(session, bank_create.bik):
            raise HTTPException(
                status_code=400,
                detail=f"Банк с БИК '{bank_create.bik}' уже существует"
            )
        
        # Проверка уникальности ИНН
        if await bank_data.check_inn_exists(session, bank_create.inn):
            raise HTTPException(
                status_code=400,
                detail=f"Банк с ИНН '{bank_create.inn}' уже существует"
            )
        
        # Создание
        bank = await bank_data.create(session, bank_create)
        
        return bank

# ========== ОБНОВЛЕНИЕ ==========

async def update_bank(
    bank_id: int,
    bank_update: BankUpdate,
    current_user: User
) -> Bank:
    """
    Обновить банк
    """
    await check_permission(current_user, "bank_modify", "изменения банков")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await bank_data.get_by_id(session, bank_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Банк с id {bank_id} не найден"
            )
        
        # Проверка уникальности названия, если оно меняется
        if bank_update.name and bank_update.name != existing.name:
            if await bank_data.check_name_exists(session, bank_update.name, bank_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Банк с названием '{bank_update.name}' уже существует"
                )
        
        # Проверка уникальности БИК, если он меняется
        if bank_update.bik and bank_update.bik != existing.bik:
            if await bank_data.check_bik_exists(session, bank_update.bik, bank_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Банк с БИК '{bank_update.bik}' уже существует"
                )
        
        # Проверка уникальности ИНН, если он меняется
        if bank_update.inn and bank_update.inn != existing.inn:
            if await bank_data.check_inn_exists(session, bank_update.inn, bank_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Банк с ИНН '{bank_update.inn}' уже существует"
                )
        
        # Обновление
        bank = await bank_data.update(session, bank_id, bank_update)
        
        return bank

# ========== УДАЛЕНИЕ ==========

async def delete_bank(
    bank_id: int,
    current_user: User
) -> bool:
    """
    Удалить банк
    """
    await check_permission(current_user, "bank_delete", "удаления банков")
    
    async with new_session() as session:
        # Проверяем существование и связанные организации
        bank = await bank_data.get_by_id(
            session, 
            bank_id, 
            load_organizations=True
        )
        
        if not bank:
            raise HTTPException(
                status_code=404,
                detail=f"Банк с id {bank_id} не найден"
            )
        
        # Проверка на наличие связанных организаций
        if bank.organizations and len(bank.organizations) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить банк '{bank.name}': есть связанные организации ({len(bank.organizations)} шт.)"
            )
        
        # Удаление
        success = await bank_data.delete(session, bank_id)
        
        return success