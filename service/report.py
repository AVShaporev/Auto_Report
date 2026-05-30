from typing import Optional, List, Tuple
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from model.user import User
from model.report import Report
from model.contract import Contract
from model.object import Object
from data import report as report_data
from schema.report import ReportCreate, ReportUpdate, ReportStatusUpdate
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
        report = await report_data.get_report_by_id(
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
    status_id: Optional[int] = None,
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
        items, total = await report_data.get_report_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            period_id=period_id,
            contract_id=contract_id,
            object_id=object_id,
            user_id=user_id,
            status_id=status_id,
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
    status_id: Optional[int] = None
) -> Tuple[List[Report], int]:
    """
    Получить отчеты текущего пользователя
    """
    await check_permission(current_user, "report_read", "просмотра своих отчетов")

    async with new_session() as session:
        items, total = await report_data.get_report_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            user_id=current_user.id,
            status_id=status_id,
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
        return await report_data.get_report_all(session, load_relations=load_relations)

async def get_report_options(
    current_user: User,
    status_id: Optional[int] = None
) -> List[Report]:
    """
    Получить минимальную информацию об отчетах для выпадающих списков
    """
    await check_permission(current_user, "report_read", "просмотра отчетов")

    async with new_session() as session:
        return await report_data.get_report_options(session, status_id=status_id)

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
        report = await report_data.get_report_by_id(
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
            "status_id": report.status_id,
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
            "status_name": report.status.name if report.status else None,
            "status_code": report.status.code if report.status else None,
            "order_id": report.order.id if report.order else None,
            "order_number": report.order.number if report.order else None,
        }

async def get_reports_paginated_with_details(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    period_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status_id: Optional[int] = None,
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
        items, total = await report_data.get_report_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            period_id=period_id,
            contract_id=contract_id,
            object_id=object_id,
            user_id=user_id,
            status_id=status_id,
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
                "status_id": item.status_id,
                "status_name": item.status.name if item.status else None,
                "status_code": item.status.code if item.status else None,
                "created_at": item.created_at,
                "period_name": item.period.name if item.period else None,
                "contract_number": item.contract.number if item.contract else None,
                "object_name": item.object.name if item.object else None,
                "user_name": item.user.name if item.user else None,
                "order_id": item.order.id if item.order else None,
                "order_number": item.order.number if item.order else None,
            })

        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_report(
    report_create: ReportCreate,
    current_user: User  # 👈 Передаем текущего пользователя
) -> Report:
    """
    Создать новый отчет.

    user_id берется из current_user, а не из запроса.
    Номер отчёта генерируется сервером по маске
    "{object_id}/{MM}/{YYYY}/{customer.short_name}/{contract.short_subject}"
    из report_create.report_period (формат "YYYY-MM").
    """
    await check_permission(current_user, "report_create", "создания отчетов")

    async with new_session() as session:
        # 1:1: заявка должна существовать и не иметь связанного отчёта.
        # Подгружаем сразу с object (нужен period_id) — это позволяет вытащить
        # period_id/contract_id/object_id, если фронт их не прислал.
        from model.order import Order as OrderModel
        order = (await session.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.object))
            .where(OrderModel.id == report_create.order_id)
        )).scalar_one_or_none()
        if not order:
            raise HTTPException(
                status_code=400,
                detail=f"Заявка с id {report_create.order_id} не существует"
            )
        if order.report_id is not None:
            raise HTTPException(
                status_code=400,
                detail=f"К заявке id {order.id} уже привязан отчёт (id {order.report_id})"
            )

        # Деривация id-шников из заявки, если их не передал фронт.
        # Если передали — должны совпасть с заявкой (защита от рассинхрона UI).
        derived_contract_id = order.contract_id
        derived_object_id = order.object_id
        derived_period_id = order.object.period_id if order.object else None

        if report_create.contract_id and report_create.contract_id != derived_contract_id:
            raise HTTPException(
                status_code=400,
                detail=(f"contract_id={report_create.contract_id} не совпадает "
                        f"с контрактом заявки ({derived_contract_id})")
            )
        if report_create.object_id and report_create.object_id != derived_object_id:
            raise HTTPException(
                status_code=400,
                detail=(f"object_id={report_create.object_id} не совпадает "
                        f"с объектом заявки ({derived_object_id})")
            )
        if report_create.period_id and report_create.period_id != derived_period_id:
            raise HTTPException(
                status_code=400,
                detail=(f"period_id={report_create.period_id} не совпадает "
                        f"с периодом объекта заявки ({derived_period_id})")
            )

        effective_contract_id = derived_contract_id
        effective_object_id = derived_object_id
        effective_period_id = derived_period_id

        if effective_period_id is None:
            raise HTTPException(
                status_code=400,
                detail="У объекта заявки не указан период обслуживания"
            )

        # Перезаписываем поля в DTO так, чтобы data-слой получил корректные id.
        report_create.contract_id = effective_contract_id
        report_create.object_id = effective_object_id
        report_create.period_id = effective_period_id

        # Проверка существования (паранойя на случай битой FK)
        checks = [
            (report_data.check_period_exists, effective_period_id, "Период"),
            (report_data.check_contract_exists, effective_contract_id, "Контракт"),
            (report_data.check_object_exists, effective_object_id, "Объект")
        ]

        for check_func, entity_id, entity_name in checks:
            if not await check_func(session, entity_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"{entity_name} с id {entity_id} не существует"
                )

        # Подгружаем контракт с заказчиком и объект для построения номера
        contract = (await session.execute(
            select(Contract)
            .options(selectinload(Contract.customer))
            .where(Contract.id == effective_contract_id)
        )).scalar_one_or_none()
        if not contract:
            raise HTTPException(status_code=400, detail="Контракт не найден")
        if not contract.customer:
            raise HTTPException(status_code=400, detail="У контракта не указан заказчик")

        obj = (await session.execute(
            select(Object).where(Object.id == effective_object_id)
        )).scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=400, detail="Объект не найден")

        # Парсим отчётный период
        try:
            year_str, month_str = report_create.report_period.split("-", 1)
            year = int(year_str)
            month = int(month_str)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=400,
                detail="Некорректный формат отчётного периода (ожидается YYYY-MM)"
            )

        short_name = (contract.customer.short_name or "").strip() or "—"
        short_subject = (contract.short_subject or "").strip() or "—"
        # В качестве «номера объекта» в номере отчёта используем
        # number_in_contract (порядковый в рамках контракта), а не глобальный id.
        generated_number = (
            f"{obj.number_in_contract}/{month:02d}/{year:04d}/"
            f"{short_name}/{short_subject}"
        )

        if await report_data.check_report_number_exists(session, generated_number):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Отчёт за {month:02d}.{year} по объекту "
                    f"№{obj.number_in_contract} (id={obj.id}) "
                    f"уже существует (номер '{generated_number}')"
                )
            )

        # Дефолтный статус для нового отчёта — 'not_approved'.
        default_status = await report_data.get_spec_status_by_code(session, 'not_approved')
        if not default_status:
            raise HTTPException(
                status_code=500,
                detail="Не найден статус 'not_approved' в справочнике spec_statuss",
            )

        # Создание — передаём user_id из current_user, сгенерированный номер и заявку
        report = await report_data.create_report(
            session,
            report_create,
            current_user.id,
            number=generated_number,
            order=order,
            status_id=default_status.id,
        )

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
        existing = await report_data.get_report_by_id(session, report_id)
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
            if await report_data.check_report_number_exists(session, update_data['number'], report_id):
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
        report = await report_data.update_report(session, report_id, report_update)
        
        return report

# ========== СМЕНА СТАТУСА ОТЧЁТА ==========

async def update_report_status(
    report_id: int,
    status_update: ReportStatusUpdate,
    current_user: User
) -> Report:
    """
    Установить статус отчёта (FK на spec_statuss).
    """
    await check_permission(current_user, "report_modify", "смены статуса отчётов")

    async with new_session() as session:
        # Проверяем, что статус существует.
        from data import spec_status as spec_status_data
        status = await spec_status_data.get_spec_status_by_id(session, status_update.status_id)
        if not status:
            raise HTTPException(
                status_code=400,
                detail=f"Статус с id {status_update.status_id} не существует",
            )

        report = await report_data.update_report_status(session, report_id, status_update.status_id)

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
        report = await report_data.get_report_by_id(
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

        # При удалении отчёта связанная заявка освобождается
        # (order.report_id → NULL через ON DELETE SET NULL)
        success = await report_data.delete_report(session, report_id)
        if success:
            # CASCADE удалит записи report_attachments в БД, файлы — отдельно с диска.
            from service.report_attachment import cleanup_report_directory
            cleanup_report_directory(report_id)
        return success