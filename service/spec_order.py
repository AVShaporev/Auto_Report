from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.spec_order import Spec_Order
from data import spec_order as spec_order_data
from schema.spec_order import SpecOrderCreate, SpecOrderUpdate
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
        permission: Название права (spec_order_read, spec_order_create и т.д.)
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

async def get_spec_order_by_id(
    spec_order_id: int,
    current_user: User,
    load_orders: bool = False
) -> Spec_Order:
    """
    Получить тип заявки по ID с проверкой прав
    """
    await check_permission(current_user, "spec_order_read", "просмотра типов заявок")
    
    async with new_session() as session:
        spec_order = await spec_order_data.get_spec_order_by_id(
            session, 
            spec_order_id, 
            load_orders=load_orders
        )
        
        if not spec_order:
            raise HTTPException(
                status_code=404,
                detail=f"Тип заявки с id {spec_order_id} не найден"
            )
        
        return spec_order

async def get_spec_orders_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Spec_Order], int]:
    """
    Получить список типов заявок с пагинацией
    """
    await check_permission(current_user, "spec_order_read", "просмотра списка типов заявок")
    
    async with new_session() as session:
        items, total = await spec_order_data.get_spec_order_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_orders=True  # Загружаем связанные заявки для подсчета
        )
        
        return items, total

async def get_all_spec_orders(
    current_user: User,
    load_orders: bool = False
) -> List[Spec_Order]:
    """
    Получить все типы заявок
    """
    await check_permission(current_user, "spec_order_read", "просмотра типов заявок")
    
    async with new_session() as session:
        return await spec_order_data.get_spec_order_all(session, load_orders=load_orders)

async def get_spec_order_options(
    current_user: User
) -> List[Spec_Order]:
    """
    Получить минимальную информацию о типах заявок для выпадающих списков
    """
    await check_permission(current_user, "spec_order_read", "просмотра типов заявок")
    
    async with new_session() as session:
        return await spec_order_data.get_spec_order_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_spec_order_with_stats(
    spec_order_id: int,
    current_user: User
) -> dict:
    """
    Получить тип заявки со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "spec_order_read", "просмотра типов заявок")
    
    async with new_session() as session:
        # Получаем тип заявки (без загрузки заявок)
        spec_order = await spec_order_data.get_spec_order_by_id(
            session, 
            spec_order_id,
            load_orders=False
        )
        
        if not spec_order:
            raise HTTPException(
                status_code=404,
                detail=f"Тип заявки с id {spec_order_id} не найден"
            )
        
        # Получаем ТОЛЬКО количество связанных заявок
        orders_count = await spec_order_data.count_orders_by_spec_order(
            session, 
            spec_order_id
        )
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": spec_order.id,
            "name": spec_order.name,
            "short_name": spec_order.short_name,
            "orders_count": orders_count
        }

async def update_spec_order_with_stats(
    spec_order_id: int,
    spec_order_update: SpecOrderUpdate,
    current_user: User
) -> dict:
    """
    Обновить тип заявки и вернуть словарь со статистикой для ответа
    """
    await check_permission(current_user, "spec_order_modify", "изменения типов заявок")

    async with new_session() as session:
        existing = await spec_order_data.get_spec_order_by_id(session, spec_order_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип заявки с id {spec_order_id} не найден"
            )

        if spec_order_update.name and spec_order_update.name != existing.name:
            if await spec_order_data.check_spec_order_name_exists(session, spec_order_update.name, spec_order_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип заявки с названием '{spec_order_update.name}' уже существует"
                )

        spec_order = await spec_order_data.update_spec_order(session, spec_order_id, spec_order_update)

        orders_count = await spec_order_data.count_orders_by_spec_order(session, spec_order_id)

        return {
            "id": spec_order.id,
            "name": spec_order.name,
            "short_name": spec_order.short_name,
            "orders_count": orders_count
        }

async def get_spec_orders_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список типов заявок со статистикой для ответа
    """
    await check_permission(current_user, "spec_order_read", "просмотра списка типов заявок")
    
    async with new_session() as session:
        # Получаем типы заявок (без загрузки заявок)
        items, total = await spec_order_data.get_spec_order_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_orders=False
        )
        
        # Для каждого типа заявки получаем количество заявок
        result_items = []
        for item in items:
            orders_count = await spec_order_data.count_orders_by_spec_order(
                session, 
                item.id
            )
            result_items.append({
                "id": item.id,
                "name": item.name,
                "short_name": item.short_name,
                "orders_count": orders_count
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_spec_order(
    spec_order_create: SpecOrderCreate,
    current_user: User
) -> Spec_Order:
    """
    Создать новый тип заявки
    """
    await check_permission(current_user, "spec_order_create", "создания типов заявок")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await spec_order_data.check_spec_order_name_exists(session, spec_order_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Тип заявки с названием '{spec_order_create.name}' уже существует"
            )
        
        # Создание
        spec_order = await spec_order_data.create_spec_order(session, spec_order_create)
        
        return spec_order

# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_order(
    spec_order_id: int,
    spec_order_update: SpecOrderUpdate,
    current_user: User
) -> Spec_Order:
    """
    Обновить тип заявки
    """
    await check_permission(current_user, "spec_order_modify", "изменения типов заявок")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await spec_order_data.get_spec_order_by_id(session, spec_order_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип заявки с id {spec_order_id} не найден"
            )
        
        # Проверка уникальности названия, если оно меняется
        if spec_order_update.name and spec_order_update.name != existing.name:
            if await spec_order_data.check_spec_order_name_exists(session, spec_order_update.name, spec_order_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип заявки с названием '{spec_order_update.name}' уже существует"
                )
        
        # Обновление
        spec_order = await spec_order_data.update_spec_order(session, spec_order_id, spec_order_update)
        
        return spec_order

# ========== УДАЛЕНИЕ ==========

async def delete_spec_order(
    spec_order_id: int,
    current_user: User
) -> bool:
    """
    Удалить тип заявки
    """
    await check_permission(current_user, "spec_order_delete", "удаления типов заявок")
    
    async with new_session() as session:
        # Проверяем существование и связанные заявки
        spec_order = await spec_order_data.get_spec_order_by_id(
            session, 
            spec_order_id, 
            load_orders=True
        )
        
        if not spec_order:
            raise HTTPException(
                status_code=404,
                detail=f"Тип заявки с id {spec_order_id} не найден"
            )

        if spec_order.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_order.name}' — она необходима для работы системы."
            )

        # Проверка на наличие связанных заявок
        if spec_order.orders and len(spec_order.orders) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить тип заявки '{spec_order.name}': есть связанные заявки ({len(spec_order.orders)} шт.)"
            )
        
        # Удаление
        success = await spec_order_data.delete_spec_order(session, spec_order_id)
        
        return success