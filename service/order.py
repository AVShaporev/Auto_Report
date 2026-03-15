from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.order import Order
from data import order as order_data
from schema.order import OrderCreate, OrderUpdate
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
        permission: Название права (order_read, order_create и т.д.)
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

async def get_order_by_id(
    order_id: int,
    current_user: User,
    load_relations: bool = False
) -> Order:
    """
    Получить заявку по ID с проверкой прав
    """
    await check_permission(current_user, "order_read", "просмотра заявок")
    
    async with new_session() as session:
        order = await order_data.get_by_id(
            session, 
            order_id, 
            load_relations=load_relations
        )
        
        if not order:
            raise HTTPException(
                status_code=404,
                detail=f"Заявка с id {order_id} не найдена"
            )
        
        return order

async def get_orders_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_order_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Tuple[List[Order], int]:
    """
    Получить список заявок с пагинацией
    """
    await check_permission(current_user, "order_read", "просмотра списка заявок")
    
    async with new_session() as session:
        items, total = await order_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_order_id=spec_order_id,
            contract_id=contract_id,
            object_id=object_id,
            user_id=user_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True  # Загружаем связанные данные для ответа
        )
        
        return items, total

async def get_orders_by_current_user(
    pagination: PaginationParams,
    current_user: User,
    status: Optional[str] = None
) -> Tuple[List[Order], int]:
    """
    Получить заявки текущего пользователя с пагинацией
    """
    await check_permission(current_user, "order_read", "просмотра своих заявок")
    
    async with new_session() as session:
        items, total = await order_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            user_id=current_user.id,
            status=status,
            load_relations=True
        )
        
        return items, total

async def get_all_orders(
    current_user: User,
    load_relations: bool = False
) -> List[Order]:
    """
    Получить все заявки
    """
    await check_permission(current_user, "order_read", "просмотра заявок")
    
    async with new_session() as session:
        return await order_data.get_all(session, load_relations=load_relations)

async def get_order_options(
    current_user: User,
    status: Optional[str] = None
) -> List[Order]:
    """
    Получить минимальную информацию о заявках для выпадающих списков
    """
    await check_permission(current_user, "order_read", "просмотра заявок")
    
    async with new_session() as session:
        return await order_data.get_options(session, status=status)

# ========== ПОЛУЧЕНИЕ С ДЕТАЛЬНОЙ ИНФОРМАЦИЕЙ ==========

async def get_order_with_details(
    order_id: int,
    current_user: User
) -> dict:
    """
    Получить заявку с детальной информацией для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "order_read", "просмотра заявок")
    
    async with new_session() as session:
        # Получаем заявку с загрузкой всех связанных данных
        order = await order_data.get_by_id(
            session, 
            order_id,
            load_relations=True
        )
        
        if not order:
            raise HTTPException(
                status_code=404,
                detail=f"Заявка с id {order_id} не найдена"
            )
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": order.id,
            "number": order.number,
            "spec_order_id": order.spec_order_id,
            "contract_id": order.contract_id,
            "object_id": order.object_id,
            "user_id": order.user_id,
            "report_id": order.report_id,
            "created_at": order.created_at,
            "description": order.description,
            "status": order.status,
            "spec_order_name": order.spec_order.name if order.spec_order else None,
            "contract_number": order.contract.number if order.contract else None,
            "object_name": order.object.name if order.object else None,
            "user_name": order.user.name if order.user else None,
            "report_number": order.report.number if order.report else None
        }

async def get_orders_paginated_with_details(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_order_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Tuple[List[dict], int]:
    """
    Получить список заявок с детальной информацией для ответа
    """
    await check_permission(current_user, "order_read", "просмотра списка заявок")
    
    async with new_session() as session:
        # Получаем заявки с загрузкой связанных данных
        items, total = await order_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_order_id=spec_order_id,
            contract_id=contract_id,
            object_id=object_id,
            user_id=user_id,
            status=status,
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
                "created_at": item.created_at,
                "status": item.status,
                "spec_order_name": item.spec_order.name if item.spec_order else None,
                "object_name": item.object.name if item.object else None,
                "user_name": item.user.name if item.user else None,
                "contract_number": item.contract.number if item.contract else None
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_order(
    order_create: OrderCreate,
    current_user: User  # 👈 Передаем текущего пользователя
) -> Order:
    """
    Создать новую заявку
    user_id берется из current_user, а не из запроса
    """
    await check_permission(current_user, "order_create", "создания заявок")
    
    async with new_session() as session:
        # Проверка уникальности номера
        if await order_data.check_number_exists(session, order_create.number):
            raise HTTPException(
                status_code=400,
                detail=f"Заявка с номером '{order_create.number}' уже существует"
            )
        
        # Проверка существования всех связанных объектов
        if not await order_data.check_spec_order_exists(session, order_create.spec_order_id):
            raise HTTPException(
                status_code=400,
                detail=f"Тип заявки с id {order_create.spec_order_id} не существует"
            )
        
        if not await order_data.check_contract_exists(session, order_create.contract_id):
            raise HTTPException(
                status_code=400,
                detail=f"Контракт с id {order_create.contract_id} не существует"
            )
        
        if not await order_data.check_object_exists(session, order_create.object_id):
            raise HTTPException(
                status_code=400,
                detail=f"Объект с id {order_create.object_id} не существует"
            )
        
        # Создание - передаем user_id из current_user
        order = await order_data.create(session, order_create, current_user.id)
        
        return order

# ========== ОБНОВЛЕНИЕ ==========

async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    current_user: User
) -> Order:
    """
    Обновить заявку
    """
    await check_permission(current_user, "order_modify", "изменения заявок")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await order_data.get_by_id(session, order_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Заявка с id {order_id} не найдена"
            )
        
        # Проверка прав на изменение (может менять только автор или админ)
        if existing.user_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете изменять только свои заявки"
            )
        
        # Проверка уникальности номера, если он меняется
        if order_update.number and order_update.number != existing.number:
            if await order_data.check_number_exists(session, order_update.number, order_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Заявка с номером '{order_update.number}' уже существует"
                )
        
        # Проверка существования связанных объектов, если они меняются
        update_data = order_update.dict(exclude_unset=True)
        
        if 'spec_order_id' in update_data and update_data['spec_order_id'] != existing.spec_order_id:
            if not await order_data.check_spec_order_exists(session, update_data['spec_order_id']):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип заявки с id {update_data['spec_order_id']} не существует"
                )
        
        if 'contract_id' in update_data and update_data['contract_id'] != existing.contract_id:
            if not await order_data.check_contract_exists(session, update_data['contract_id']):
                raise HTTPException(
                    status_code=400,
                    detail=f"Контракт с id {update_data['contract_id']} не существует"
                )
        
        if 'object_id' in update_data and update_data['object_id'] != existing.object_id:
            if not await order_data.check_object_exists(session, update_data['object_id']):
                raise HTTPException(
                    status_code=400,
                    detail=f"Объект с id {update_data['object_id']} не существует"
                )
        
        if 'report_id' in update_data and update_data['report_id'] is not None:
            if not await order_data.check_report_exists(session, update_data['report_id']):
                raise HTTPException(
                    status_code=400,
                    detail=f"Отчет с id {update_data['report_id']} не существует"
                )
        
        # Обновление
        order = await order_data.update(session, order_id, order_update)
        
        return order

# ========== ОБНОВЛЕНИЕ СТАТУСА ==========

async def update_order_status(
    order_id: int,
    status: str,
    current_user: User
) -> Order:
    """
    Обновить статус заявки
    """
    await check_permission(current_user, "order_modify", "изменения статуса заявок")
    
    valid_statuses = ["new", "in_progress", "completed", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый статус. Допустимые значения: {', '.join(valid_statuses)}"
        )
    
    async with new_session() as session:
        # Проверяем существование и права
        existing = await order_data.get_by_id(session, order_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Заявка с id {order_id} не найдена"
            )
        
        # Проверка прав (может менять только автор или админ)
        if existing.user_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете изменять статус только своих заявок"
            )
        
        order = await order_data.update_status(session, order_id, status)
        
        return order

# ========== УДАЛЕНИЕ ==========

async def delete_order(
    order_id: int,
    current_user: User
) -> bool:
    """
    Удалить заявку
    """
    await check_permission(current_user, "order_delete", "удаления заявок")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        order = await order_data.get_by_id(
            session, 
            order_id, 
            load_relations=True
        )
        
        if not order:
            raise HTTPException(
                status_code=404,
                detail=f"Заявка с id {order_id} не найдена"
            )
        
        # Проверка прав на удаление (может удалять только автор или админ)
        if order.user_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете удалять только свои заявки"
            )
        
        # Проверка на наличие связанного отчета
        if order.report:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить заявку '{order.number}': есть связанный отчет"
            )
        
        # Удаление
        success = await order_data.delete(session, order_id)
        
        return success