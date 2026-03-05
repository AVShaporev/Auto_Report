from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.period import Period
from data import period as period_data
from schema.period import PeriodCreate, PeriodUpdate
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
        permission: Название права (period_read, period_create и т.д.)
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

async def get_period_by_id(
    period_id: int,
    current_user: User,
    load_relations: bool = False
) -> Period:
    """
    Получить период по ID с проверкой прав
    """
    await check_permission(current_user, "period_read", "просмотра периодов")
    
    async with new_session() as session:
        period = await period_data.get_by_id(
            session, 
            period_id, 
            load_relations=load_relations
        )
        
        if not period:
            raise HTTPException(
                status_code=404,
                detail=f"Период с id {period_id} не найден"
            )
        
        return period

async def get_periods_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Period], int]:
    """
    Получить список периодов с пагинацией
    """
    await check_permission(current_user, "period_read", "просмотра списка периодов")
    
    async with new_session() as session:
        items, total = await period_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True  # Загружаем связанные данные для подсчета
        )
        
        return items, total

async def get_all_periods(
    current_user: User,
    load_relations: bool = False
) -> List[Period]:
    """
    Получить все периоды
    """
    await check_permission(current_user, "period_read", "просмотра периодов")
    
    async with new_session() as session:
        return await period_data.get_all(session, load_relations=load_relations)

async def get_period_options(
    current_user: User
) -> List[Period]:
    """
    Получить минимальную информацию о периодах для выпадающих списков
    """
    await check_permission(current_user, "period_read", "просмотра периодов")
    
    async with new_session() as session:
        return await period_data.get_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_period_with_stats(
    period_id: int,
    current_user: User
) -> dict:
    """
    Получить период со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "period_read", "просмотра периодов")
    
    async with new_session() as session:
        # Получаем период (без загрузки связанных данных)
        period = await period_data.get_by_id(
            session, 
            period_id,
            load_relations=False
        )
        
        if not period:
            raise HTTPException(
                status_code=404,
                detail=f"Период с id {period_id} не найден"
            )
        
        # Получаем количество связанных объектов
        objects_count = await period_data.count_objects(session, period_id)
        reports_count = await period_data.count_reports(session, period_id)
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": period.id,
            "name": period.name,
            "period": period.period,
            "objects_count": objects_count,
            "reports_count": reports_count
        }

async def get_periods_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список периодов со статистикой для ответа
    """
    await check_permission(current_user, "period_read", "просмотра списка периодов")
    
    async with new_session() as session:
        # Получаем периоды (без загрузки связанных данных)
        items, total = await period_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=False
        )
        
        # Для каждого периода получаем статистику
        result_items = []
        for item in items:
            objects_count = await period_data.count_objects(session, item.id)
            reports_count = await period_data.count_reports(session, item.id)
            
            result_items.append({
                "id": item.id,
                "name": item.name,
                "period": item.period,
                "objects_count": objects_count,
                "reports_count": reports_count
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_period(
    period_create: PeriodCreate,
    current_user: User
) -> Period:
    """
    Создать новый период
    """
    await check_permission(current_user, "period_create", "создания периодов")
    
    async with new_session() as session:
        # Проверка уникальности названия
        if await period_data.check_name_exists(session, period_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Период с названием '{period_create.name}' уже существует"
            )
        
        # Проверка уникальности периодичности
        if await period_data.check_period_exists(session, period_create.period):
            raise HTTPException(
                status_code=400,
                detail=f"Период с периодичностью '{period_create.period}' уже существует"
            )
        
        # Создание
        period = await period_data.create(session, period_create)
        
        return period

# ========== ОБНОВЛЕНИЕ ==========

async def update_period(
    period_id: int,
    period_update: PeriodUpdate,
    current_user: User
) -> Period:
    """
    Обновить период
    """
    await check_permission(current_user, "period_modify", "изменения периодов")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await period_data.get_by_id(session, period_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Период с id {period_id} не найден"
            )
        
        # Проверка уникальности названия, если оно меняется
        if period_update.name and period_update.name != existing.name:
            if await period_data.check_name_exists(session, period_update.name, period_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Период с названием '{period_update.name}' уже существует"
                )
        
        # Проверка уникальности периодичности, если она меняется
        if period_update.period and period_update.period != existing.period:
            if await period_data.check_period_exists(session, period_update.period, period_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Период с периодичностью '{period_update.period}' уже существует"
                )
        
        # Обновление
        period = await period_data.update(session, period_id, period_update)
        
        return period

# ========== УДАЛЕНИЕ ==========

async def delete_period(
    period_id: int,
    current_user: User
) -> bool:
    """
    Удалить период
    """
    await check_permission(current_user, "period_delete", "удаления периодов")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        period = await period_data.get_by_id(
            session, 
            period_id, 
            load_relations=True
        )
        
        if not period:
            raise HTTPException(
                status_code=404,
                detail=f"Период с id {period_id} не найден"
            )
        
        # Проверка на наличие связанных объектов
        if period.objects and len(period.objects) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить период '{period.name}': есть связанные объекты ({len(period.objects)} шт.)"
            )
        
        if period.reports and len(period.reports) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить период '{period.name}': есть связанные отчеты ({len(period.reports)} шт.)"
            )
        
        # Удаление
        success = await period_data.delete(session, period_id)
        
        return success