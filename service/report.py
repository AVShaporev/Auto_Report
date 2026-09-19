from typing import Optional, List, Tuple
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from model.user import User
from model.report import Report
from model.contract import Contract
from model.object import Object
from model.spec_order_status import Spec_Order_Status
from data import report as report_data
from service.activity_log import log_activity
from service import customer_signature
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


# Статусы, из которых автор без report_modify может отправить свой отчёт
# на утверждение (совпадают с mobile services/reportStatuses.js).
SUBMITTED_STATUS_NAME = 'На утверждении'
APPROVED_STATUS_NAME = 'Утверждён'
AUTHOR_EDITABLE_STATUS_NAMES = ('В работе', 'Отклонён')


def can_moderate_reports(current_user: User) -> bool:
    return bool(getattr(current_user.role, "report_modify", False))


async def check_report_author_permission(current_user: User, action: str) -> None:
    """Правка своего отчёта: report_modify или report_create.

    Инженеру с одним report_create иначе нельзя ни поправить описание, ни
    отправить на утверждение созданный им же отчёт. Проверка «свой отчёт»
    остаётся в вызывающей функции.
    """
    if not (can_moderate_reports(current_user)
            or getattr(current_user.role, "report_create", False)):
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
    assigned_to_id: Optional[int] = None,
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
            assigned_to_id=assigned_to_id,
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
            .options(
                selectinload(OrderModel.object),
                selectinload(OrderModel.spec_order),
            )
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
        short_order = (order.spec_order.short_name or "").strip() if order.spec_order else "—"
        short_order = short_order or "—"

        # seq — порядковый номер отчёта такого же типа (spec_order) для
        # этого объекта в этом месяце. Аналогично order-number:
        # позволяет иметь несколько отчётов на объект/месяц по разным
        # заявкам одного или разного типа (аварийные, плановые и т.п.).
        from sqlalchemy import func, extract
        count_stmt = (
            select(func.count())
            .select_from(Report)
            .join(OrderModel, OrderModel.report_id == Report.id)
            .where(
                Report.object_id == effective_object_id,
                extract('year', Report.created_at) == year,
                extract('month', Report.created_at) == month,
                OrderModel.spec_order_id == order.spec_order_id,
            )
        )
        existing_same_kind = (await session.execute(count_stmt)).scalar() or 0
        seq = existing_same_kind + 1

        # В качестве «номера объекта» в номере отчёта — number_in_contract
        # (порядковый в рамках контракта), а не глобальный id.
        generated_number = (
            f"{obj.number_in_contract}/{month:02d}/{year:04d}/"
            f"{short_name}/{short_subject}/{short_order}/{seq}"
        )

        # На случай гонки или ручных правок номеров — финальная проверка.
        if await report_data.check_report_number_exists(session, generated_number):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Не удалось сгенерировать уникальный номер отчёта "
                    f"('{generated_number}' уже существует). Повторите попытку."
                )
            )

        # Дефолтный статус для нового отчёта — is_default = true из
        # spec_report_statuses («В работе» по сиду f3a4b5c6d7e8). Партиал-
        # уникальный индекс гарантирует ровно одну такую строку, а сид —
        # что она есть; если её нет — миграция сломана, кидаем 500.
        default_status = await report_data.get_default_spec_report_status(session)
        if not default_status:
            raise HTTPException(
                status_code=500,
                detail="spec_report_statuses не имеет is_default=true — миграция сломана.",
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

        await log_activity(
            session, current_user,
            action='create', entity='report', entity_id=report.id,
            summary=f'Создал отчёт №{report.number}',
        )

        # Подпись представителя заказчика узором — вместе с отчётом (онлайн
        # токен или офлайн-узор из очереди мобилки).
        if report_create.signature_token or report_create.signature_offline:
            await customer_signature.apply_signature(
                session, report, order.id,
                token=report_create.signature_token, offline=report_create.signature_offline)
            await session.commit()
            await log_activity(
                session, current_user,
                action='update', entity='report', entity_id=report.id,
                summary=_signature_summary(report),
            )

        # Создание отчёта = инженер начал работу по заявке. Автоматически
        # переводим заявку в статус «В работе» (если она ещё не там или в
        # более продвинутом состоянии). Специально проверяем именно "не
        # равно", а не "меньше" — админ может руками поставить «Выполнена»
        # или «Отменена», тогда не откатываем.
        in_progress_status = (await session.execute(
            select(Spec_Order_Status).where(Spec_Order_Status.name == 'В работе')
        )).scalar_one_or_none()
        if in_progress_status and order.status_id != in_progress_status.id:
            # Меняем только если сейчас «Новая» (is_default) — из
            # «Выполнена»/«Отменена» назад не откатываем, это админ-решение.
            current_status = (await session.execute(
                select(Spec_Order_Status).where(Spec_Order_Status.id == order.status_id)
            )).scalar_one_or_none()
            if current_status and current_status.is_default:
                order.status_id = in_progress_status.id
                await log_activity(
                    session, current_user,
                    action='update', entity='order', entity_id=order.id,
                    summary=(f'Заявка №{order.number}: статус → «В работе» '
                             f'(создан отчёт №{report.number})'),
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
    await check_report_author_permission(current_user, "изменения отчетов")

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
        
        # Подпись: токен/офлайн-узор — поставить, clear_signature — убрать.
        # Проверяем до записи остальных полей, чтобы 400 не оставил отчёт
        # полуизменённым.
        signature_given = bool(report_update.signature_token or report_update.signature_offline
                               or report_update.clear_signature)
        if signature_given:
            customer_signature.ensure_not_approved(existing)

        # Обновление (user_id нельзя изменить через update)
        report = await report_data.update_report(session, report_id, report_update)

        if signature_given:
            if report_update.clear_signature:
                customer_signature.clear_signature(report)
            else:
                order_id = report.order.id if report.order else None
                await customer_signature.apply_signature(
                    session, report, order_id,
                    token=report_update.signature_token, offline=report_update.signature_offline)
            await session.commit()
            await session.refresh(report)
            for k in ('signature_token', 'signature_offline', 'clear_signature'):
                update_data.pop(k, None)
            update_data['signature'] = _signature_summary(report)

        changed_keys = ', '.join(sorted(update_data.keys())) or 'нет полей'
        await log_activity(
            session, current_user,
            action='update', entity='report', entity_id=report.id,
            summary=f'Изменил отчёт №{report.number}: {changed_keys}',
            details=update_data,
        )
        return report

# ========== СМЕНА СТАТУСА ОТЧЁТА ==========

async def update_report_status(
    report_id: int,
    status_update: ReportStatusUpdate,
    current_user: User
) -> Report:
    """
    Установить статус отчёта (FK на spec_report_statuses).
    """
    await check_report_author_permission(current_user, "смены статуса отчётов")

    async with new_session() as session:
        # Проверяем, что статус существует. Report.status_id — FK на
        # spec_report_statuses (не старую spec_statuss, которая для Issue).
        from data import spec_report_status as spec_report_status_data
        status = await spec_report_status_data.get_spec_report_status_by_id(
            session, status_update.status_id,
        )
        if not status:
            raise HTTPException(
                status_code=400,
                detail=f"Статус отчёта с id {status_update.status_id} не существует в spec_report_statuses",
            )

        # Без report_modify (инженер-автор) — только отправить свой отчёт на
        # утверждение. Утверждать/отклонять может лишь тот, у кого report_modify.
        if not can_moderate_reports(current_user):
            existing = await report_data.get_report_by_id(session, report_id)
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Отчет с id {report_id} не найден"
                )
            if existing.user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Вы можете отправлять на утверждение только свои отчёты"
                )
            current_status_name = existing.status.name if existing.status else None
            if (status.name != SUBMITTED_STATUS_NAME
                    or current_status_name not in AUTHOR_EDITABLE_STATUS_NAMES):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Без права изменения отчётов можно только отправить свой отчёт "
                        "из «В работе» или «Отклонён» на утверждение"
                    ),
                )

        if status.name in (SUBMITTED_STATUS_NAME, APPROVED_STATUS_NAME):
            current = await report_data.get_report_by_id(session, report_id)
            if (current and current.object and current.object.requires_signature
                    and current.signature_status != 'verified'):
                raise HTTPException(status_code=400, detail=(
                    "На объекте нужна подпись представителя заказчика: попросите "
                    "его подписать отчёт знаком в мобильном приложении."
                    + (" Последняя подпись не подтвердилась — знак не совпал."
                       if current.signature_status == 'failed' else "")
                ))

        report = await report_data.update_report_status(session, report_id, status_update.status_id)

        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Отчет с id {report_id} не найден"
            )

        await log_activity(
            session, current_user,
            action='change_status', entity='report', entity_id=report.id,
            summary=f'Сменил статус отчёта №{report.number} → {status.name}',
            details={'new_status_id': status_update.status_id},
        )

        if status.name == APPROVED_STATUS_NAME:
            await _resolve_fixed_issues(session, report, current_user)
        return report


def _signature_summary(report: Report) -> str:
    if report.signature_status == 'verified':
        return (f'Отчёт №{report.number}: подписан представителем заказчика '
                f'{report.signer_name} (код {report.signature_code})')
    if report.signature_status == 'failed':
        return (f'Отчёт №{report.number}: подпись {report.signer_name} не подтверждена — '
                f'знак не совпал')
    return f'Отчёт №{report.number}: подпись убрана'


async def _resolve_fixed_issues(session, report: Report, current_user: User) -> None:
    """Отчёт утверждён → неисправности, которые устраняли его заявки, «Устранена».

    Связь: отчёт ← заявки (orders.report_id) ← неисправности (issues.order_id,
    «заявка на устранение», backend 1.0.61). Трогаем только неустранённые
    (is_resolved=false): статус с кодом 'resolved', дата устранения — сегодня.
    Обратного хода нет: если отчёт потом «разутвердят», неисправность остаётся
    устранённой — статус можно поменять вручную.
    """
    from model.issue import Issue
    from model.order import Order
    from data import spec_status as spec_status_data

    issues = (await session.execute(
        select(Issue)
        .join(Order, Issue.order_id == Order.id)
        .where(Order.report_id == report.id, Issue.is_resolved.is_(False))
    )).scalars().all()
    if not issues:
        return

    resolved = await spec_status_data.get_spec_status_by_code(session, 'resolved')
    if not resolved:
        # Справочник статусов неисправностей без системного 'resolved' — не
        # гадаем по названию, просто не трогаем.
        return

    today = date.today()
    for issue in issues:
        issue.status_id = resolved.id
        issue.is_resolved = True
        issue.resolved_date = today
    await session.commit()

    for issue in issues:
        await log_activity(
            session, current_user,
            action='change_status', entity='issue', entity_id=issue.id,
            summary=(
                f'Неисправность №{issue.number} → {resolved.name} '
                f'(утверждён отчёт №{report.number} по заявке на устранение)'
            ),
            details={'report_id': report.id, 'resolved_date': today.isoformat()},
        )

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
        report_number = report.number
        success = await report_data.delete_report(session, report_id)
        if success:
            # CASCADE удалит записи report_attachments в БД, файлы — отдельно с диска.
            from service.report_attachment import cleanup_report_directory
            cleanup_report_directory(report_id)
            await log_activity(
                session, current_user,
                action='delete', entity='report', entity_id=report_id,
                summary=f'Удалил отчёт №{report_number}',
            )
        return success