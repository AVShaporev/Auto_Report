from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_contract import Spec_Contract
from data import spec_contract as spec_contract_data
from schema.spec_contract import SpecContractCreate, SpecContractUpdate
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

async def get_spec_contract_by_id(
                                    spec_contract_id: int,
                                    current_user: User,
                                    load_contracts: bool = False
                                    ) -> Spec_Contract:
    """
    Получить тип договора по ID с проверкой прав
    """
    await check_permission(current_user, "spec_contract_read", "просмотра типов договоров")
    
    async with new_session() as session:
        spec_contract = await spec_contract_data.get_spec_contract_by_id(
                                                            session, 
                                                            spec_contract_id, 
                                                            load_contracts
                                                            )
        
        if not spec_contract:
            raise HTTPException(
                status_code=404,
                detail=f"Тип договора с id {spec_contract_id} не найден"
            )
        
        return spec_contract

async def get_spec_contracts_paginated(
                                        pagination: PaginationParams,
                                        current_user: User,
                                        search: Optional[str] = None,
                                        sort_by: str = "name",
                                        sort_order: str = "asc"
                                        ) -> Tuple[List[Spec_Contract], int]:
    """
    Получить список типов договоров с пагинацией
    """
    await check_permission(current_user, "spec_contract_read", "просмотра списка типов договоров")
    
    async with new_session() as session:
        items, total = await spec_contract_data.get_spec_contract_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_contracts=True
        )
        
        return items, total

async def get_all_spec_contracts(
    current_user: User,
    load_contracts: bool = False
) -> List[Spec_Contract]:
    """
    Получить все типы договоров
    """
    await check_permission(current_user, "spec_contract_read", "просмотра типов договоров")
    
    async with new_session() as session:
        return await spec_contract_data.get_spec_contract_all(session, load_contracts)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_contract_with_stats(
    spec_contract_id: int,
    current_user: User
) -> dict:
    """
    Получить тип договора со статистикой для ответа
    """
    await check_permission(current_user, "spec_contract_read", "просмотра типов договоров")

    async with new_session() as session:
        spec_contract = await spec_contract_data.get_spec_contract_by_id(
            session,
            spec_contract_id,
            load_contracts=False
        )

        if not spec_contract:
            raise HTTPException(
                status_code=404,
                detail=f"Тип договора с id {spec_contract_id} не найден"
            )

        contracts_count = await spec_contract_data.count_contracts_by_spec_contract(session, spec_contract_id)

        return {
            "id": spec_contract.id,
            "name": spec_contract.name,
            "contracts_count": contracts_count
        }

async def get_spec_contracts_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список типов договоров со статистикой для ответа
    """
    await check_permission(current_user, "spec_contract_read", "просмотра списка типов договоров")

    async with new_session() as session:
        items, total = await spec_contract_data.get_spec_contract_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_contracts=False
        )

        result_items = []
        for item in items:
            contracts_count = await spec_contract_data.count_contracts_by_spec_contract(session, item.id)
            result_items.append({
                "id": item.id,
                "name": item.name,
                "contracts_count": contracts_count
            })

        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_contract(
    spec_contract_create: SpecContractCreate,
    current_user: User
) -> Spec_Contract:
    """
    Создать новый тип договора
    """
    await check_permission(current_user, "spec_contract_create", "создания типов договоров")
    
    async with new_session() as session:
        # Проверка уникальности названия
        exists = await spec_contract_data.check_spec_contract_name_exists(
            session, 
            spec_contract_create.name
        )
        if exists:
            raise HTTPException(
                status_code=400,
                detail=f"Тип договора с названием '{spec_contract_create.name}' уже существует"
            )
        
        # Создание
        spec_contract = await spec_contract_data.create_spec_contract(session, spec_contract_create)
        
        return spec_contract

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_contract(
    spec_contract_id: int,
    spec_contract_update: SpecContractUpdate,
    current_user: User
) -> Spec_Contract:
    """
    Обновить тип договора
    """
    await check_permission(current_user, "spec_contract_modify", "изменения типов договоров")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await spec_contract_data.get_spec_contract_by_id(session, spec_contract_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип договора с id {spec_contract_id} не найден"
            )
        
        # Проверка уникальности названия, если оно меняется
        if spec_contract_update.name and spec_contract_update.name != existing.name:
            exists = await spec_contract_data.check_spec_contract_name_exists(
                session, 
                spec_contract_update.name, 
                spec_contract_id
            )
            if exists:
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип договора с названием '{spec_contract_update.name}' уже существует"
                )
        
        # Обновление
        spec_contract = await spec_contract_data.update_spec_contract(
            session,
            spec_contract_id,
            spec_contract_update
        )
        
        return spec_contract

async def update_spec_contract_with_stats(
    spec_contract_id: int,
    spec_contract_update: SpecContractUpdate,
    current_user: User
) -> dict:
    """
    Обновить тип договора и вернуть результат со статистикой (contracts_count).
    Парный к get_spec_contract_with_stats — чтобы api-слою не приходилось лазать в data.
    """
    # update_spec_contract уже делает check_permission и валидации — не дублируем
    spec_contract = await update_spec_contract(spec_contract_id, spec_contract_update, current_user)

    async with new_session() as session:
        contracts_count = await spec_contract_data.count_contracts_by_spec_contract(session, spec_contract_id)

    return {
        "id": spec_contract.id,
        "name": spec_contract.name,
        "contracts_count": contracts_count
    }

# ========== УДАЛЕНИЕ ==========

async def delete_spec_contract(
    spec_contract_id: int,
    current_user: User
) -> bool:
    """
    Удалить тип договора
    """
    await check_permission(current_user, "spec_contract_delete", "удаления типов договоров")
    
    async with new_session() as session:
        # Проверяем существование и связанные договоры
        spec_contract = await spec_contract_data.get_spec_contract_by_id(
            session, 
            spec_contract_id, 
            load_contracts=True
        )
        
        if not spec_contract:
            raise HTTPException(
                status_code=404,
                detail=f"Тип договора с id {spec_contract_id} не найден"
            )

        if spec_contract.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_contract.name}' — она необходима для работы системы."
            )

        # Проверка на наличие связанных договоров
        if spec_contract.contracts and len(spec_contract.contracts) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить тип договора '{spec_contract.name}': есть связанные договоры ({len(spec_contract.contracts)} шт.)"
            )
        
        # Удаление
        success = await spec_contract_data.delete_spec_contract(session, spec_contract_id)
        
        return success