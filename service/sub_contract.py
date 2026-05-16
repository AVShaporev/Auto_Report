from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.sub_contract import Sub_Contract
from data import sub_contract as sub_contract_data
from schema.sub_contract import SubContractCreate, SubContractUpdate
from schema.pagination import PaginationParams
from database.database import new_session
from datetime import date

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
        permission: Название права (sub_contract_read, sub_contract_create и т.д.)
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

async def get_sub_contract_by_id(
    sub_contract_id: int,
    current_user: User,
    load_relations: bool = False
) -> Sub_Contract:
    """
    Получить дополнительное соглашение по ID с проверкой прав
    """
    await check_permission(current_user, "sub_contract_read", "просмотра дополнительных соглашений")
    
    async with new_session() as session:
        sub_contract = await sub_contract_data.get_sub_contract_by_id(
            session, 
            sub_contract_id, 
            load_relations=load_relations
        )
        
        if not sub_contract:
            raise HTTPException(
                status_code=404,
                detail=f"Дополнительное соглашение с id {sub_contract_id} не найдено"
            )
        
        return sub_contract

async def get_sub_contracts_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    contract_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "date_of_consclusion",
    sort_order: str = "desc"
) -> Tuple[List[Sub_Contract], int]:
    """
    Получить список дополнительных соглашений с пагинацией
    """
    await check_permission(current_user, "sub_contract_read", "просмотра списка дополнительных соглашений")
    
    async with new_session() as session:
        items, total = await sub_contract_data.get_sub_contract_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            contract_id=contract_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True  # Загружаем связанный контракт для ответа
        )
        
        return items, total

async def get_all_sub_contracts(
    current_user: User,
    load_relations: bool = False
) -> List[Sub_Contract]:
    """
    Получить все дополнительные соглашения
    """
    await check_permission(current_user, "sub_contract_read", "просмотра дополнительных соглашений")
    
    async with new_session() as session:
        return await sub_contract_data.get_sub_contract_all(session, load_relations=load_relations)

async def get_sub_contract_options(
    current_user: User,
    contract_id: Optional[int] = None
) -> List[Sub_Contract]:
    """
    Получить минимальную информацию о дополнительных соглашениях для выпадающих списков
    """
    await check_permission(current_user, "sub_contract_read", "просмотра дополнительных соглашений")
    
    async with new_session() as session:
        return await sub_contract_data.get_sub_contract_options(session, contract_id=contract_id)

# ========== ПОЛУЧЕНИЕ С ДЕТАЛЬНОЙ ИНФОРМАЦИЕЙ ==========

async def get_sub_contract_with_details(
    sub_contract_id: int,
    current_user: User
) -> dict:
    """
    Получить дополнительное соглашение с детальной информацией для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "sub_contract_read", "просмотра дополнительных соглашений")
    
    async with new_session() as session:
        # Получаем дополнительное соглашение с загрузкой контракта
        sub_contract = await sub_contract_data.get_sub_contract_by_id(
            session, 
            sub_contract_id,
            load_relations=True
        )
        
        if not sub_contract:
            raise HTTPException(
                status_code=404,
                detail=f"Дополнительное соглашение с id {sub_contract_id} не найдено"
            )
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": sub_contract.id,
            "number": sub_contract.number,
            "date_of_consclusion": sub_contract.date_of_consclusion,
            "subject": sub_contract.subject,
            "contract_id": sub_contract.contract_id,
            "contract_number": sub_contract.contract_subject.number if sub_contract.contract_subject else None
        }

async def get_sub_contracts_paginated_with_details(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    contract_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "date_of_consclusion",
    sort_order: str = "desc"
) -> Tuple[List[dict], int]:
    """
    Получить список дополнительных соглашений с детальной информацией для ответа
    """
    await check_permission(current_user, "sub_contract_read", "просмотра списка дополнительных соглашений")
    
    async with new_session() as session:
        # Получаем дополнительные соглашения с загрузкой контрактов
        items, total = await sub_contract_data.get_sub_contract_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            contract_id=contract_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )
        
        # Формируем результат
        result_items = []
        for item in items:
            result_items.append({
                "id": item.id,
                "number": item.number,
                "date_of_consclusion": item.date_of_consclusion,
                "subject": item.subject,
                "contract_number": item.contract_subject.number if item.contract_subject else None
            })
        
        return result_items, total

# ========== ПОЛУЧЕНИЕ ПО КОНТРАКТУ ==========

async def get_sub_contracts_by_contract(
    contract_id: int,
    current_user: User
) -> List[dict]:
    """
    Получить все дополнительные соглашения по контракту
    """
    await check_permission(current_user, "sub_contract_read", "просмотра дополнительных соглашений")
    
    async with new_session() as session:
        # Проверяем существование контракта
        if not await sub_contract_data.check_contract_exists(session, contract_id):
            raise HTTPException(
                status_code=404,
                detail=f"Контракт с id {contract_id} не найден"
            )
        
        sub_contracts = await sub_contract_data.get_sub_contract_by_contract(session, contract_id)
        
        return [
            {
                "id": item.id,
                "number": item.number,
                "date_of_consclusion": item.date_of_consclusion,
                "subject": item.subject
            }
            for item in sub_contracts
        ]

# ========== СОЗДАНИЕ ==========

async def create_sub_contract(
    sub_contract_create: SubContractCreate,
    current_user: User
) -> Sub_Contract:
    """
    Создать новое дополнительное соглашение
    """
    await check_permission(current_user, "sub_contract_create", "создания дополнительных соглашений")
    
    async with new_session() as session:
        # Проверка уникальности номера
        if await sub_contract_data.check_sub_contract_number_exists(session, sub_contract_create.number):
            raise HTTPException(
                status_code=400,
                detail=f"Дополнительное соглашение с номером '{sub_contract_create.number}' уже существует"
            )
        
        # Проверка существования контракта
        if not await sub_contract_data.check_contract_exists(session, sub_contract_create.contract_id):
            raise HTTPException(
                status_code=400,
                detail=f"Контракт с id {sub_contract_create.contract_id} не существует"
            )
        
        # Создание
        sub_contract = await sub_contract_data.create_sub_contract(session, sub_contract_create)
        
        return sub_contract

# ========== ОБНОВЛЕНИЕ ==========

async def update_sub_contract(
    sub_contract_id: int,
    sub_contract_update: SubContractUpdate,
    current_user: User
) -> Sub_Contract:
    """
    Обновить дополнительное соглашение
    """
    await check_permission(current_user, "sub_contract_modify", "изменения дополнительных соглашений")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await sub_contract_data.get_sub_contract_by_id(session, sub_contract_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Дополнительное соглашение с id {sub_contract_id} не найдено"
            )
        
        # Проверка уникальности номера, если он меняется
        if sub_contract_update.number and sub_contract_update.number != existing.number:
            if await sub_contract_data.check_sub_contract_number_exists(session, sub_contract_update.number, sub_contract_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Дополнительное соглашение с номером '{sub_contract_update.number}' уже существует"
                )
        
        # Проверка существования контракта, если он меняется
        if sub_contract_update.contract_id and sub_contract_update.contract_id != existing.contract_id:
            if not await sub_contract_data.check_contract_exists(session, sub_contract_update.contract_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Контракт с id {sub_contract_update.contract_id} не существует"
                )
        
        # Обновление
        sub_contract = await sub_contract_data.update_sub_contract(session, sub_contract_id, sub_contract_update)
        
        return sub_contract

# ========== УДАЛЕНИЕ ==========

async def delete_sub_contract(
    sub_contract_id: int,
    current_user: User
) -> bool:
    """
    Удалить дополнительное соглашение
    """
    await check_permission(current_user, "sub_contract_delete", "удаления дополнительных соглашений")
    
    async with new_session() as session:
        # Проверяем существование
        sub_contract = await sub_contract_data.get_sub_contract_by_id(session, sub_contract_id)
        
        if not sub_contract:
            raise HTTPException(
                status_code=404,
                detail=f"Дополнительное соглашение с id {sub_contract_id} не найдено"
            )
        
        # Удаление
        success = await sub_contract_data.delete_sub_contract(session, sub_contract_id)
        
        return success