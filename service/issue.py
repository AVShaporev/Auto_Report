from typing import Optional, List, Tuple
from fastapi import HTTPException
from sqlalchemy import select, func, extract
from sqlalchemy.orm import selectinload

from model.user import User
from model.issue import Issue
from model.objects_equipment import Objects_Equipment
from model.object import Object
from model.contract import Contract
from model.organization import Organization
from data import issue as issue_data
from schema.issue import IssueCreate, IssueUpdate, IssueStatusUpdate
from schema.pagination import PaginationParams
from database.database import new_session  # 👈 используем new_session вместо new_session
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
        permission: Название права (issue_read, issue_create и т.д.)
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

async def get_issue_by_id(
    issue_id: int,
    current_user: User,
    load_relations: bool = False
) -> Issue:
    """
    Получить неисправность по ID с проверкой прав
    """
    await check_permission(current_user, "issue_read", "просмотра неисправностей")
    
    async with new_session() as session:
        issue = await issue_data.get_issue_by_id(
            session, 
            issue_id, 
            load_relations=load_relations
        )
        
        if not issue:
            raise HTTPException(
                status_code=404,
                detail=f"Неисправность с id {issue_id} не найдена"
            )
        
        return issue

async def get_issues_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    object_id: Optional[int] = None,
    equipment_id: Optional[int] = None,
    status_id: Optional[int] = None,
    priority_id: Optional[int] = None,
    is_resolved: Optional[bool] = None,
    is_critical: Optional[bool] = None,
    reported_by_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "detected_date",
    sort_order: str = "desc"
) -> Tuple[List[Issue], int]:
    """
    Получить список неисправностей с пагинацией
    """
    await check_permission(current_user, "issue_read", "просмотра списка неисправностей")

    async with new_session() as session:
        items, total = await issue_data.get_issue_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            object_id=object_id,
            equipment_id=equipment_id,
            status_id=status_id,
            priority_id=priority_id,
            is_resolved=is_resolved,
            is_critical=is_critical,
            reported_by_id=reported_by_id,
            assigned_to_id=assigned_to_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )
        
        return items, total

async def get_issues_by_current_user(
    pagination: PaginationParams,
    current_user: User,
    status_id: Optional[int] = None,
    is_resolved: Optional[bool] = None
) -> Tuple[List[Issue], int]:
    """
    Получить неисправности, сообщенные текущим пользователем
    """
    await check_permission(current_user, "issue_read", "просмотра своих неисправностей")

    async with new_session() as session:
        items, total = await issue_data.get_issue_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            reported_by_id=current_user.id,
            status_id=status_id,
            is_resolved=is_resolved,
            load_relations=True
        )
        
        return items, total

async def get_issues_assigned_to_current_user(
    pagination: PaginationParams,
    current_user: User,
    status_id: Optional[int] = None,
    is_resolved: Optional[bool] = None
) -> Tuple[List[Issue], int]:
    """
    Получить неисправности, назначенные текущему пользователю
    """
    await check_permission(current_user, "issue_read", "просмотра назначенных неисправностей")

    async with new_session() as session:
        items, total = await issue_data.get_issue_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            assigned_to_id=current_user.id,
            status_id=status_id,
            is_resolved=is_resolved,
            load_relations=True
        )
        
        return items, total

async def get_issues_by_object(
    object_id: int,
    current_user: User
) -> List[Issue]:
    """
    Получить все неисправности по объекту
    """
    await check_permission(current_user, "issue_read", "просмотра неисправностей объекта")
    
    async with new_session() as session:
        # Проверяем существование объекта через objects_equipment
        issues = await issue_data.get_issue_by_object(session, object_id)
        return issues

async def get_issues_by_equipment(
    equipment_id: int,
    current_user: User
) -> List[Issue]:
    """
    Получить все неисправности по оборудованию
    """
    await check_permission(current_user, "issue_read", "просмотра неисправностей оборудования")
    
    async with new_session() as session:
        issues = await issue_data.get_issue_by_equipment(session, equipment_id)
        return issues

# ========== ПОЛУЧЕНИЕ С ДЕТАЛЬНОЙ ИНФОРМАЦИЕЙ ==========

async def get_issue_with_details(
    issue_id: int,
    current_user: User
) -> dict:
    """
    Получить неисправность с детальной информацией для ответа
    """
    await check_permission(current_user, "issue_read", "просмотра неисправностей")
    
    async with new_session() as session:
        issue = await issue_data.get_issue_by_id(
            session, 
            issue_id,
            load_relations=True
        )
        
        if not issue:
            raise HTTPException(
                status_code=404,
                detail=f"Неисправность с id {issue_id} не найдена"
            )
        
        # Инвентарный номер хранится на связке Objects_Equipment (per-instance),
        # объект/оборудование — через её отношения.
        object_id = None
        object_name = None
        equipment_id = None
        equipment_name = None
        equipment_inventory_number = None

        if issue.object_equipment:
            object_id = issue.object_equipment.object_id
            equipment_id = issue.object_equipment.equipment_id
            equipment_inventory_number = issue.object_equipment.inventory_number
            if issue.object_equipment.object:
                object_name = issue.object_equipment.object.name
            if issue.object_equipment.equipment:
                equipment_name = issue.object_equipment.equipment.name
        
        return {
            "id": issue.id,
            "number": issue.number,
            "title": issue.title,
            "description": issue.description,
            "status_id": issue.status_id,
            "status_name": issue.status.name if issue.status else None,
            "status_code": issue.status.code if issue.status else None,
            "priority_id": issue.priority_id,
            "priority_name": issue.priority.name if issue.priority else None,
            "priority_code": issue.priority.code if issue.priority else None,
            "detected_date": issue.detected_date,
            "resolved_date": issue.resolved_date,
            "is_resolved": issue.is_resolved,
            "is_critical": issue.is_critical,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "object_equipment_id": issue.object_equipment_id,
            "reported_by_id": issue.reported_by_id,
            "assigned_to_id": issue.assigned_to_id,
            "object_id": object_id,
            "object_name": object_name,
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "equipment_inventory_number": equipment_inventory_number,
            "reported_by_name": issue.reported_by.name if issue.reported_by else None,
            "assigned_to_name": issue.assigned_to.name if issue.assigned_to else None
        }

async def get_issues_paginated_with_details(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    object_id: Optional[int] = None,
    equipment_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    status_id: Optional[int] = None,
    priority_id: Optional[int] = None,
    is_resolved: Optional[bool] = None,
    is_critical: Optional[bool] = None,
    reported_by_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "detected_date",
    sort_order: str = "desc"
) -> Tuple[List[dict], int]:
    """
    Получить список неисправностей с детальной информацией для ответа
    """
    await check_permission(current_user, "issue_read", "просмотра списка неисправностей")

    async with new_session() as session:
        items, total = await issue_data.get_issue_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            object_id=object_id,
            equipment_id=equipment_id,
            contract_id=contract_id,
            status_id=status_id,
            priority_id=priority_id,
            is_resolved=is_resolved,
            is_critical=is_critical,
            reported_by_id=reported_by_id,
            assigned_to_id=assigned_to_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )
        
        result_items = []
        for item in items:
            object_id_ = None
            object_name = None
            equipment_id_ = None
            equipment_name = None

            if item.object_equipment:
                object_id_ = item.object_equipment.object_id
                equipment_id_ = item.object_equipment.equipment_id
                if item.object_equipment.object:
                    object_name = item.object_equipment.object.name
                if item.object_equipment.equipment:
                    equipment_name = item.object_equipment.equipment.name

            result_items.append({
                "id": item.id,
                "number": item.number,
                "title": item.title,
                "status_id": item.status_id,
                "status_name": item.status.name if item.status else None,
                "status_code": item.status.code if item.status else None,
                "priority_id": item.priority_id,
                "priority_name": item.priority.name if item.priority else None,
                "priority_code": item.priority.code if item.priority else None,
                "detected_date": item.detected_date,
                "resolved_date": item.resolved_date,
                "is_resolved": item.is_resolved,
                "is_critical": item.is_critical,
                "created_at": item.created_at,
                "object_id": object_id_,
                "object_name": object_name,
                "equipment_id": equipment_id_,
                "equipment_name": equipment_name,
                "reported_by_name": item.reported_by.name if item.reported_by else None,
                "assigned_to_name": item.assigned_to.name if item.assigned_to else None
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_issue(
    issue_create: IssueCreate,
    current_user: User  # 👈 reported_by_id берется из current_user
) -> Issue:
    """
    Создать новую неисправность
    reported_by_id автоматически берется из current_user
    """
    await check_permission(current_user, "issue_create", "создания неисправностей")

    async with new_session() as session:
        # Проверяем существование связи объект-оборудование
        if not await issue_data.check_issue_object_equipment_exists(session, issue_create.object_equipment_id):
            raise HTTPException(
                status_code=400,
                detail=f"Связь объекта с оборудованием с id {issue_create.object_equipment_id} не существует"
            )

        # Проверка существования назначенного пользователя (если указан)
        if issue_create.assigned_to_id:
            if not await issue_data.check_issue_user_exists(session, issue_create.assigned_to_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Пользователь с id {issue_create.assigned_to_id} не существует"
                )

        # Проверка существования приоритета
        from data import spec_priority as spec_priority_data
        if not await spec_priority_data.get_spec_priority_by_id(session, issue_create.priority_id):
            raise HTTPException(
                status_code=400,
                detail=f"Приоритет с id {issue_create.priority_id} не существует"
            )

        # Подгружаем связку с объектом и его контрактом/заказчиком —
        # нужно для генерации номера неисправности.
        link = (await session.execute(
            select(Objects_Equipment)
            .options(
                selectinload(Objects_Equipment.object)
                    .selectinload(Object.contract)
                    .selectinload(Contract.customer),
            )
            .where(Objects_Equipment.id == issue_create.object_equipment_id)
        )).scalar_one_or_none()
        if not link or not link.object:
            raise HTTPException(status_code=400, detail="Связь объекта с оборудованием не найдена")
        obj = link.object
        contract = obj.contract
        if not contract:
            raise HTTPException(status_code=400, detail="У объекта не указан контракт")
        if not contract.customer:
            raise HTTPException(status_code=400, detail="У контракта не указан заказчик")

        today = date.today()
        year, month = today.year, today.month

        # Порядковый номер в текущем месяце по паре (object, contract) — issues привязаны
        # к объекту через Objects_Equipment, поэтому нужен join.
        count_stmt = (
            select(func.count(Issue.id))
            .join(Objects_Equipment, Issue.object_equipment_id == Objects_Equipment.id)
            .where(
                Objects_Equipment.object_id == obj.id,
                Objects_Equipment.equipment_id != None,  # noqa: E711
                Objects_Equipment.object_id == obj.id,
                extract('year', Issue.created_at) == year,
                extract('month', Issue.created_at) == month,
            )
        )
        existing_count = (await session.execute(count_stmt)).scalar() or 0
        seq = existing_count + 1

        short_customer = (contract.customer.short_name or "").strip() or "—"
        short_subject = (contract.short_subject or "").strip() or "—"

        generated_number = (
            f"{obj.number_in_contract}/{month:02d}/{year:04d}/"
            f"{short_customer}/{short_subject}/Н/{seq}"
        )

        # Финальная проверка уникальности (на случай гонок и ручных правок).
        if await issue_data.check_issue_number_exists(session, generated_number):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Не удалось сгенерировать уникальный номер неисправности "
                    f"('{generated_number}' уже существует). Повторите попытку."
                )
            )

        # Статус по умолчанию для новой неисправности — код 'new'
        from data import spec_status as spec_status_data
        default_status = await spec_status_data.get_spec_status_by_code(session, 'new')
        if not default_status:
            raise HTTPException(
                status_code=500,
                detail="Не найден статус по умолчанию (code='new') в справочнике статусов"
            )

        issue = await issue_data.create_issue(
            session,
            issue_create,
            current_user.id,
            default_status.id,
            number=generated_number,
        )

        return issue

# ========== ОБНОВЛЕНИЕ ==========

async def update_issue(
    issue_id: int,
    issue_update: IssueUpdate,
    current_user: User
) -> Issue:
    """
    Обновить неисправность
    """
    await check_permission(current_user, "issue_modify", "изменения неисправностей")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await issue_data.get_issue_by_id(session, issue_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Неисправность с id {issue_id} не найдена"
            )
        
        # Проверка прав (может изменять только автор или админ)
        if existing.reported_by_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете изменять только свои неисправности"
            )
        
        # Проверка уникальности номера, если он меняется
        update_data = issue_update.dict(exclude_unset=True)
        
        if 'number' in update_data and update_data['number'] != existing.number:
            if await issue_data.check_issue_number_exists(session, update_data['number'], issue_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Неисправность с номером '{update_data['number']}' уже существует"
                )
        
        # ✅ ИСПРАВЛЕНО: проверяем существование связи объект-оборудование, если она меняется
        if 'object_equipment_id' in update_data and update_data['object_equipment_id'] != existing.object_equipment_id:
            if not await issue_data.check_issue_object_equipment_exists(session, update_data['object_equipment_id']):
                raise HTTPException(
                    status_code=400,
                    detail=f"Связь объекта с оборудованием с id {update_data['object_equipment_id']} не существует"
                )
        
        if 'assigned_to_id' in update_data and update_data['assigned_to_id'] != existing.assigned_to_id:
            if update_data['assigned_to_id'] is not None:
                if not await issue_data.check_issue_user_exists(session, update_data['assigned_to_id']):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Пользователь с id {update_data['assigned_to_id']} не существует"
                    )

        if 'priority_id' in update_data and update_data['priority_id'] != existing.priority_id:
            from data import spec_priority as spec_priority_data
            if not await spec_priority_data.get_spec_priority_by_id(session, update_data['priority_id']):
                raise HTTPException(
                    status_code=400,
                    detail=f"Приоритет с id {update_data['priority_id']} не существует"
                )
        
        # Обновление
        issue = await issue_data.update_issue(session, issue_id, issue_update)
        
        return issue

# ========== ОБНОВЛЕНИЕ СТАТУСА ==========

async def update_issue_status(
    issue_id: int,
    status_update: IssueStatusUpdate,
    current_user: User
) -> Issue:
    """
    Обновить статус неисправности
    """
    await check_permission(current_user, "issue_modify", "изменения статуса неисправностей")

    async with new_session() as session:
        # Проверяем существование
        existing = await issue_data.get_issue_by_id(session, issue_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Неисправность с id {issue_id} не найдена"
            )

        # Проверяем существование статуса и валидируем дату устранения по его коду
        from data import spec_status as spec_status_data
        new_status = await spec_status_data.get_spec_status_by_id(session, status_update.status_id)
        if not new_status:
            raise HTTPException(
                status_code=400,
                detail=f"Статус с id {status_update.status_id} не существует"
            )

        if new_status.code == 'resolved' and not status_update.resolved_date:
            raise HTTPException(
                status_code=400,
                detail="Для статуса с кодом 'resolved' необходимо указать дату устранения"
            )

        # Обновление статуса
        issue = await issue_data.update_issue_status(
            session,
            issue_id,
            status_update.status_id,
            status_update.resolved_date
        )

        return issue

# ========== НАЗНАЧЕНИЕ ОТВЕТСТВЕННОГО ==========

async def assign_issue(
    issue_id: int,
    user_id: int,
    current_user: User
) -> Issue:
    """
    Назначить ответственного за неисправность
    """
    await check_permission(current_user, "issue_modify", "назначения ответственных")
    
    async with new_session() as session:
        # Проверяем существование неисправности
        existing = await issue_data.get_issue_by_id(session, issue_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Неисправность с id {issue_id} не найдена"
            )
        
        # Проверяем существование пользователя
        if not await issue_data.check_issue_user_exists(session, user_id):
            raise HTTPException(
                status_code=400,
                detail=f"Пользователь с id {user_id} не существует"
            )
        
        # Назначение
        issue = await issue_data.assign_issue_to_user(session, issue_id, user_id)
        
        return issue

# ========== УДАЛЕНИЕ ==========

async def delete_issue(
    issue_id: int,
    current_user: User
) -> bool:
    """
    Удалить неисправность
    """
    await check_permission(current_user, "issue_delete", "удаления неисправностей")
    
    async with new_session() as session:
        # Проверяем существование
        issue = await issue_data.get_issue_by_id(session, issue_id)
        
        if not issue:
            raise HTTPException(
                status_code=404,
                detail=f"Неисправность с id {issue_id} не найдена"
            )
        
        # Проверка прав (может удалять только автор или админ)
        if issue.reported_by_id != current_user.id and not current_user.role.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Вы можете удалять только свои неисправности"
            )
        
        # Удаление
        success = await issue_data.delete_issue(session, issue_id)
        if success:
            # CASCADE удалит записи issue_attachments в БД, файлы — отдельно с диска.
            from service.issue_attachment import cleanup_issue_directory
            cleanup_issue_directory(issue_id)

        return success