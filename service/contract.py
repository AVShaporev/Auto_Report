from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.contract import Contract
from data import contract as contract_data
from service.activity_log import log_activity
from data import spec_contract as spec_contract_data
from data import organization as organization_data
from schema.contract import ContractCreate, ContractUpdate
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
        permission: Название права (contract_read, contract_create и т.д.)
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

async def get_contract_by_id(
    contract_id: int,
    current_user: User,
    load_relations: bool = False
) -> Contract:
    """
    Получить контракт по ID с проверкой прав
    """
    await check_permission(current_user, "contract_read", "просмотра контрактов")
    
    async with new_session() as session:
        contract = await contract_data.get_contract_by_id(
            session, 
            contract_id, 
            load_relations=load_relations
        )
        
        if not contract:
            raise HTTPException(
                status_code=404,
                detail=f"Контракт с id {contract_id} не найден"
            )
        
        return contract

async def get_contracts_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_contract_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    executor_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    type_contract: Optional[str] = None,
    sort_by: str = "number",
    sort_order: str = "asc"
) -> Tuple[List[Contract], int]:
    """
    Получить список контрактов с пагинацией
    """
    await check_permission(current_user, "contract_read", "просмотра списка контрактов")
    
    async with new_session() as session:
        items, total = await contract_data.get_contract_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_contract_id=spec_contract_id,
            customer_id=customer_id,
            executor_id=executor_id,
            date_from=date_from,
            date_to=date_to,
            type_contract=type_contract,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True  # Загружаем связанные данные для ответа
        )
        
        return items, total

async def get_all_contracts(
    current_user: User,
    load_relations: bool = False
) -> List[Contract]:
    """
    Получить все контракты
    """
    await check_permission(current_user, "contract_read", "просмотра контрактов")
    
    async with new_session() as session:
        return await contract_data.get_contract_all(session, load_relations=load_relations)

async def get_contract_options(
    current_user: User
) -> List[Contract]:
    """
    Получить минимальную информацию о контрактах для выпадающих списков
    """
    await check_permission(current_user, "contract_read", "просмотра контрактов")
    
    async with new_session() as session:
        return await contract_data.get_contract_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_contract_with_stats(
    contract_id: int,
    current_user: User
) -> dict:
    """
    Получить контракт со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "contract_read", "просмотра контрактов")
    
    async with new_session() as session:
        # Получаем контракт с загрузкой связанных данных
        contract = await contract_data.get_contract_by_id(
            session, 
            contract_id,
            load_relations=True
        )
        
        if not contract:
            raise HTTPException(
                status_code=404,
                detail=f"Контракт с id {contract_id} не найден"
            )
        
        # Получаем статистику
        sub_contracts_count = await contract_data.count_contract_sub_contracts(session, contract_id)
        objects_count = await contract_data.count_contract_objects(session, contract_id)
        reports_count = await contract_data.count_contract_reports(session, contract_id)
        orders_count = await contract_data.count_contract_orders(session, contract_id)
        issues_count = await contract_data.count_contract_issues(session, contract_id)
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": contract.id,
            "number": contract.number,
            "date_of_consclusion": contract.date_of_consclusion,
            "date_of_completion": contract.date_of_completion,
            "summ": contract.summ,
            "subject": contract.subject,
            "short_subject": contract.short_subject,
            "type_contract": contract.type_contract,
            "spec_contract_id": contract.spec_contract_id,
            "customer_id": contract.customer_id,
            "executor_id": contract.executor_id,
            "spec_contract_name": contract.spec_contract.name if contract.spec_contract else None,
            "customer_name": contract.customer.name if contract.customer else None,
            "executor_name": contract.executor.name if contract.executor else None,
            "sub_contracts_count": sub_contracts_count,
            "objects_count": objects_count,
            "reports_count": reports_count,
            "orders_count": orders_count,
            "issues_count": issues_count,
            "created_at": contract.created_at,
            "updated_at": contract.updated_at,
        }

async def get_contracts_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_contract_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    executor_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    type_contract: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "number",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список контрактов со статистикой для ответа
    """
    await check_permission(current_user, "contract_read", "просмотра списка контрактов")
    
    async with new_session() as session:
        # Получаем контракты с загрузкой связанных данных
        items, total = await contract_data.get_contract_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_contract_id=spec_contract_id,
            customer_id=customer_id,
            executor_id=executor_id,
            date_from=date_from,
            date_to=date_to,
            type_contract=type_contract,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )
        
        # Для каждого контракта получаем статистику
        result_items = []
        for item in items:
            result_items.append({
                "id": item.id,
                "number": item.number,
                "date_of_consclusion": item.date_of_consclusion,
                "date_of_completion": item.date_of_completion,
                "summ": item.summ,
                "short_subject": item.short_subject,
                "type_contract": item.type_contract,
                "spec_contract_name": item.spec_contract.name if item.spec_contract else None,
                "customer_id": item.customer_id,
                "customer_name": item.customer.short_name if item.customer else None,
                "executor_id": item.executor_id,
                "executor_name": item.executor.short_name if item.executor else None,
                "objects_count": len(item.objects) if item.objects else 0
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_contract(
    contract_create: ContractCreate,
    current_user: User
) -> Contract:
    """
    Создать новый контракт
    """
    await check_permission(current_user, "contract_create", "создания контрактов")
    
    async with new_session() as session:
        # Проверка уникальности номера
        if await contract_data.check_number_contract_exists(session, contract_create.number):
            raise HTTPException(
                status_code=400,
                detail=f"Контракт с номером '{contract_create.number}' уже существует"
            )
        
        # Проверка существования типа контракта
        if not await contract_data.check_contract_spec_contract_exists(session, contract_create.spec_contract_id):
            raise HTTPException(
                status_code=400,
                detail=f"Тип контракта с id {contract_create.spec_contract_id} не существует"
            )
        
        # Проверка существования заказчика
        if not await contract_data.check_contract_organization_exists(session, contract_create.customer_id):
            raise HTTPException(
                status_code=400,
                detail=f"Организация-заказчик с id {contract_create.customer_id} не существует"
            )
        
        # Проверка существования подрядчика
        if not await contract_data.check_contract_organization_exists(session, contract_create.executor_id):
            raise HTTPException(
                status_code=400,
                detail=f"Организация-подрядчик с id {contract_create.executor_id} не существует"
            )
        
        # Проверка дат
        if contract_create.date_of_completion <= contract_create.date_of_consclusion:
            raise HTTPException(
                status_code=400,
                detail="Дата завершения должна быть позже даты заключения"
            )
        
        # Создание
        contract = await contract_data.create_contract(session, contract_create)

        await log_activity(
            session, current_user,
            action='create', entity='contract', entity_id=contract.id,
            summary=f'Создал договор №{contract.number}',
        )
        return contract

# ========== ОБНОВЛЕНИЕ ==========

async def update_contract(
    contract_id: int,
    contract_update: ContractUpdate,
    current_user: User
) -> Contract:
    """
    Обновить контракт
    """
    await check_permission(current_user, "contract_modify", "изменения контрактов")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await contract_data.get_contract_by_id(session, contract_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Контракт с id {contract_id} не найден"
            )
        
        # Проверка уникальности номера, если он меняется
        if contract_update.number and contract_update.number != existing.number:
            if await contract_data.check_number_contract_exists(session, contract_update.number, contract_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Контракт с номером '{contract_update.number}' уже существует"
                )
        
        # Проверка существования типа контракта, если он меняется
        if contract_update.spec_contract_id and contract_update.spec_contract_id != existing.spec_contract_id:
            if not await contract_data.check_contract_spec_contract_exists(session, contract_update.spec_contract_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип контракта с id {contract_update.spec_contract_id} не существует"
                )
        
        # Проверка существования заказчика, если он меняется
        if contract_update.customer_id and contract_update.customer_id != existing.customer_id:
            if not await contract_data.check_contract_organization_exists(session, contract_update.customer_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Организация-заказчик с id {contract_update.customer_id} не существует"
                )
        
        # Проверка существования подрядчика, если он меняется
        if contract_update.executor_id and contract_update.executor_id != existing.executor_id:
            if not await contract_data.check_contract_organization_exists(session, contract_update.executor_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Организация-подрядчик с id {contract_update.executor_id} не существует"
                )
        
        # Проверка дат, если они меняются
        date_from = contract_update.date_of_consclusion or existing.date_of_consclusion
        date_to = contract_update.date_of_completion or existing.date_of_completion
        if date_to <= date_from:
            raise HTTPException(
                status_code=400,
                detail="Дата завершения должна быть позже даты заключения"
            )
        
        # Обновление
        update_data = contract_update.dict(exclude_unset=True)
        contract = await contract_data.update_contract(session, contract_id, contract_update)

        changed_keys = ', '.join(sorted(update_data.keys())) or 'нет полей'
        await log_activity(
            session, current_user,
            action='update', entity='contract', entity_id=contract.id,
            summary=f'Изменил договор №{contract.number}: {changed_keys}',
            details=update_data,
        )
        return contract

# ========== УДАЛЕНИЕ ==========

async def delete_contract(
    contract_id: int,
    current_user: User
) -> bool:
    """
    Удалить контракт
    """
    await check_permission(current_user, "contract_delete", "удаления контрактов")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        contract = await contract_data.get_contract_by_id(
            session, 
            contract_id, 
            load_relations=True
        )
        
        if not contract:
            raise HTTPException(
                status_code=404,
                detail=f"Контракт с id {contract_id} не найден"
            )
        
        # Проверка на наличие связанных объектов
        if contract.objects and len(contract.objects) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить контракт '{contract.number}': есть связанные объекты ({len(contract.objects)} шт.)"
            )
        
        if contract.reports and len(contract.reports) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить контракт '{contract.number}': есть связанные отчеты ({len(contract.reports)} шт.)"
            )
        
        if contract.orders and len(contract.orders) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить контракт '{contract.number}': есть связанные заявки ({len(contract.orders)} шт.)"
            )
        
        if contract.sub_contract_subjects and len(contract.sub_contract_subjects) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить контракт '{contract.number}': есть связанные доп. соглашения ({len(contract.sub_contract_subjects)} шт.)"
            )
        
        # Удаление
        contract_number = contract.number
        success = await contract_data.delete_contract(session, contract_id)

        if success:
            await log_activity(
                session, current_user,
                action='delete', entity='contract', entity_id=contract_id,
                summary=f'Удалил договор №{contract_number}',
            )
        return success