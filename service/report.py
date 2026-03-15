from typing import Optional, List, Tuple
from fastapi import HTTPException
from model.user import User
from model.report import Report
from data import report as report_data
from schema.report import ReportCreate, ReportUpdate, ReportApprove
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
        permission: Название права (report_read, report_create и т.д.)
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

async def get_report_by_id(
    report_id: int,
    current_user: User,
    load_relations: bool = False
) -> Report:
    """
    Получить отчет по ID с проверкой прав
    """
    await check_permission(current_user, "report_read", "просмотра отчетов")
    
    async with new_session() as session:
        report = await report_data.get_by_id(
            session, 
            report_id, 
            load_relations=load_relations
        )
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Отчет с id {report_id} не найден"
            )
        
        return report

async def get_reports_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    period_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    check_pass: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Tuple[List[Report], int]:
    """
    Получить список отчетов с пагинацией
    """
    await check_permission(current_user, "report_read", "просмотра списка отчетов")
    
    async with new_session() as session:
        items, total = await report_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            period_id=period_id,
            contract_id=contract_id,
            object_id=object_id,
            user_id=user_id,
            check_pass=check_pass,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True  # Загружаем связанные данные для ответа
        )
        
        return items, total

async def get_reports_by_current_user(
    pagination: PaginationParams,
    current_user: User,
    check_pass: Optional[bool] = None
) -> Tuple[List[Report], int]:
    """
    Получить отчеты текущего пользователя
    """
    await check_permission(current_user, "report_read", "просмотра своих отчетов")
    
    async with new_session() as session:
        items, total = await report_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            user_id=current_user.id,
            check_pass=check_pass,
            load_relations=True
        )
        
        return items, total

async def get_all_reports(
    current_user: User,
    load_relations: bool = False
) -> List[Report]:
    """
    Получить все отчеты
    """
    await check_permission(current_user, "report_read", "просмотра отчетов")
    
    async with new_session() as session:
        return await report_data.get_all(session, load_relations=load_relations)

async def get_report_options(
    current_user: User,
    check_pass: Optional[bool] = None
) -> List[Report]:
    """
    Получить минимальную информацию об отчетах для выпадающих списков
    """
    await check_permission(current_user, "report_read", "просмотра отчетов")
    
    async with new_session() as session:
        return await report_data.get_options(session, check_pass=check_pass)

# ========== ПОЛУЧЕНИЕ С ДЕТАЛЬНОЙ ИНФОРМАЦИЕЙ ==========

async def get_report_with_details(
    report_id: int,
    current_user: User
) -> dict:
    """
    Получить отчет с детальной информацией для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "report_read", "просмотра отчетов")
    
    async with new_session() as session:
        report = await report_data.get_by_id(
            session, 
            report_id,
            load_relations=True
        )
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Отчет с id {report_id} не найден"
            )
        
        return {
            "id": report.id,
            "number": report.number,
            "check_pass": report.check_pass,
            "period_id": report.period_id,
            "contract_id": report.contract_id,
            "object_id": report.object_id,
            "user_id": report.user_id,
            "created_at": report.created_at,
            "description": report.description,
            "period_name": report.period.name if report.period else None,
            "contract_number": report.contract.number if report.contract else None,
            "object_name": report.object.name if report.object else None,
            "user_name": report.user.name if report.user else None,
            "order_number": report.order.number if report.order else None
        }

async def get_reports_paginated_with_details(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    period_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    check_pass: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Tuple[List[dict], int]:
    """
    Получить список отчетов с детальной информацией для ответа
    """
    await check_permission(current_user, "report_read", "просмотра списка отчетов")
    
    async with new_session() as session:
        items, total = await report_data.get_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            period_id=period_id,
            contract_id=contract_id,
            object_id=object_id,
            user_id=user_id,
            check_pass=check_pass,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )
        
        result_items = []
        for item in items:
            result_items.append({
                "id": item.id,
                "number": item.number,
                "check_pass": item.check_pass,
                "created_at": item.created_at,
                "period_name": item.period.name if item.period else None,
                "contract_number": item.contract.number if item.contract else None,
                "object_name": item.object.name if item.object else None,
                "user_name": item.user.name if item.user else None
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_report(
    report_create: ReportCreate,
    current_user: User  # 👈 Передаем текущего пользователя
) -> Report:
    """
    Создать новый отчет
    user_id берется из current_user, а не из запроса
    """
    await check_permission(current_user, "report_create", "создания отчетов")
    
    async with new_session() as session:
        # Проверка уникальности номера
        if await report_data.check_number_exists(session, report_create.number):
            raise HTTPException(
                status_code=400,
                detail=f"Отчет с номером '{report_create.number}' уже существует"
            )
        
        # Проверка существования всех связанных объектов
        checks = [
            (report_data.check_period_exists, report_create.period_id, "Период"),
            (report_data.check_contract_exists, report_create.contract_id, "Контракт"),
            (report_data.check_object_exists, report_create.object_id, "Объект")
        ]
        
        for check_func, entity_id, entity_name in checks:
            if not await check_func(session, entity_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"{entity_name} с id {entity_id} не существует"
                )
        
        # Создание - передаем user_id из current_user
        report = await report_data.create(session, report_create, current_user.id)
        
        return report

# ========== ОБНОВЛЕНИЕ ==========

async def update_report(
    report_id: int,
    report_update: ReportUpdate,
    current_user: User
) -> Report:
    """
    Обновить отчет
    """
    await check_permission(current_user, "report_modify", "изменения отчетов")
    
    async with new_session() as session:
        existing = await report_data.get_by_id(session, report_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Отчет с id {report_id} не найден"
            )
        
        # Проверка прав (может изменять только автор или админ)
        if existing.user_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете изменять только свои отчеты"
            )
        
        # Проверка уникальности номера, если он меняется
        update_data = report_update.dict(exclude_unset=True)
        
        if 'number' in update_data and update_data['number'] != existing.number:
            if await report_data.check_number_exists(session, update_data['number'], report_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Отчет с номером '{update_data['number']}' уже существует"
                )
        
        # Проверка существования связанных объектов, если они меняются
        checks = [
            ('period_id', report_data.check_period_exists, "Период"),
            ('contract_id', report_data.check_contract_exists, "Контракт"),
            ('object_id', report_data.check_object_exists, "Объект")
        ]
        
        for field, check_func, entity_name in checks:
            if field in update_data and update_data[field] != getattr(existing, field):
                if not await check_func(session, update_data[field]):
                    raise HTTPException(
                        status_code=400,
                        detail=f"{entity_name} с id {update_data[field]} не существует"
                    )
        
        # Обновление (user_id нельзя изменить через update)
        report = await report_data.update(session, report_id, report_update)
        
        return report

# ========== УТВЕРЖДЕНИЕ ОТЧЕТА ==========

async def approve_report(
    report_id: int,
    approve_data: ReportApprove,
    current_user: User
) -> Report:
    """
    Утвердить или отклонить отчет
    """
    await check_permission(current_user, "report_modify", "утверждения отчетов")
    
    async with new_session() as session:
        report = await report_data.approve(session, report_id, approve_data.check_pass)
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Отчет с id {report_id} не найден"
            )
        
        return report

# ========== УДАЛЕНИЕ ==========

async def delete_report(
    report_id: int,
    current_user: User
) -> bool:
    """
    Удалить отчет
    """
    await check_permission(current_user, "report_delete", "удаления отчетов")
    
    async with new_session() as session:
        report = await report_data.get_by_id(
            session, 
            report_id, 
            load_relations=True
        )
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Отчет с id {report_id} не найден"
            )
        
        # Проверка прав (может удалять только автор или админ)
        if report.user_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете удалять только свои отчеты"
            )
        
        # Проверка на наличие связанной заявки
        if report.order:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить отчет '{report.number}': есть связанная заявка"
            )
        
        success = await report_data.delete(session, report_id)
        return success