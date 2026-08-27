from typing import Optional, List, Tuple
from fastapi import HTTPException
from sqlalchemy import select, func, extract, update as sa_update
from sqlalchemy.orm import selectinload
from datetime import date

from model.user import User
from model.order import Order
from model.contract import Contract
from model.object import Object
from model.spec_order import Spec_Order
from data import order as order_data
from service.activity_log import log_activity
from schema.order import OrderCreate, OrderUpdate
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
        order = await order_data.get_order_by_id(
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
    spec_order_id: Optional[List[int]] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status_id: Optional[List[int]] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    region_id: Optional[List[int]] = None,
    arial_id: Optional[List[int]] = None,
    locality_id: Optional[List[int]] = None,
    street_id: Optional[List[int]] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Tuple[List[Order], int]:
    """
    Получить список заявок с пагинацией
    """
    await check_permission(current_user, "order_read", "просмотра списка заявок")

    async with new_session() as session:
        items, total = await order_data.get_order_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_order_id=spec_order_id,
            contract_id=contract_id,
            object_id=object_id,
            user_id=user_id,
            status_id=status_id,
            date_from=date_from,
            date_to=date_to,
            region_id=region_id,
            arial_id=arial_id,
            locality_id=locality_id,
            street_id=street_id,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True  # Загружаем связанные данные для ответа
        )

        return items, total

async def get_orders_by_current_user(
    pagination: PaginationParams,
    current_user: User,
    status_id: Optional[List[int]] = None
) -> Tuple[List[Order], int]:
    """
    Получить заявки текущего пользователя с пагинацией
    """
    await check_permission(current_user, "order_read", "просмотра своих заявок")

    async with new_session() as session:
        items, total = await order_data.get_order_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            user_id=current_user.id,
            status_id=status_id,
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
        return await order_data.get_order_all(session, load_relations=load_relations)

async def get_order_options(
    current_user: User,
    status_id: Optional[int] = None
) -> List[Order]:
    """
    Получить минимальную информацию о заявках для выпадающих списков
    """
    await check_permission(current_user, "order_read", "просмотра заявок")

    async with new_session() as session:
        return await order_data.get_order_options(session, status_id=status_id)

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
        order = await order_data.get_order_by_id(
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
            "status_id": order.status_id,
            "status_name": order.spec_order_status.name if order.spec_order_status else None,
            "spec_order_name": order.spec_order.name if order.spec_order else None,
            "contract_number": order.contract.number if order.contract else None,
            "object_name": order.object.name if order.object else None,
            "user_name": order.user.name if order.user else None,
            "assigned_to_id": order.assigned_to_id,
            "assigned_to_name": order.assigned_to.name if order.assigned_to else None,
            "report_number": order.report.number if order.report else None
        }

async def get_orders_paginated_with_details(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    spec_order_id: Optional[List[int]] = None,
    contract_id: Optional[int] = None,
    object_id: Optional[int] = None,
    user_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    status_id: Optional[List[int]] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    region_id: Optional[List[int]] = None,
    arial_id: Optional[List[int]] = None,
    locality_id: Optional[List[int]] = None,
    street_id: Optional[List[int]] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Tuple[List[dict], int]:
    """
    Получить список заявок с детальной информацией для ответа
    """
    await check_permission(current_user, "order_read", "просмотра списка заявок")

    async with new_session() as session:
        # Получаем заявки с загрузкой связанных данных
        items, total = await order_data.get_order_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            spec_order_id=spec_order_id,
            contract_id=contract_id,
            object_id=object_id,
            user_id=user_id,
            assigned_to_id=assigned_to_id,
            status_id=status_id,
            date_from=date_from,
            date_to=date_to,
            region_id=region_id,
            arial_id=arial_id,
            locality_id=locality_id,
            street_id=street_id,
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
                "status_id": item.status_id,
                "status_name": item.spec_order_status.name if item.spec_order_status else None,
                "report_id": item.report_id,
                "spec_order_id": item.spec_order_id,
                "contract_id": item.contract_id,
                "object_id": item.object_id,
                "period_id": item.object.period_id if item.object else None,
                "spec_order_name": item.spec_order.name if item.spec_order else None,
                "object_name": item.object.name if item.object else None,
                "user_name": item.user.name if item.user else None,
                "assigned_to_id": item.assigned_to_id,
                "assigned_to_name": item.assigned_to.name if item.assigned_to else None,
                "contract_number": item.contract.number if item.contract else None
            })

        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_order(
    order_create: OrderCreate,
    current_user: User
) -> Order:
    """
    Создать новую заявку.

    user_id берется из current_user. Номер генерируется сервером по маске
    "{object_id}/{MM}/{YYYY}/{customer.short_name}/{contract.short_subject}/{spec_order.short_name}/{N}",
    где N — порядковый номер заявки в текущем месяце по паре (object, contract).
    """
    await check_permission(current_user, "order_create", "создания заявок")

    async with new_session() as session:
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

        if order_create.assigned_to_id and not await order_data.check_user_exists(
            session, order_create.assigned_to_id
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Пользователь с id {order_create.assigned_to_id} не существует",
            )

        # Подгружаем контракт с заказчиком и тип заявки — нужно для маски номера.
        contract = (await session.execute(
            select(Contract)
            .options(selectinload(Contract.customer))
            .where(Contract.id == order_create.contract_id)
        )).scalar_one_or_none()
        if not contract:
            raise HTTPException(status_code=400, detail="Контракт не найден")
        if not contract.customer:
            raise HTTPException(status_code=400, detail="У контракта не указан заказчик")

        spec_order = await session.get(Spec_Order, order_create.spec_order_id)
        if not spec_order:
            raise HTTPException(status_code=400, detail="Тип заявки не найден")

        # number_in_contract — порядковый номер объекта в рамках своего
        # контракта; используется в номере заявки вместо глобального object_id.
        obj = await session.get(Object, order_create.object_id)
        if not obj:
            raise HTTPException(status_code=400, detail="Объект не найден")

        today = date.today()
        year, month = today.year, today.month

        # Порядковый номер в текущем месяце по паре (object, contract).
        count_stmt = select(func.count()).select_from(Order).where(
            Order.object_id == order_create.object_id,
            Order.contract_id == order_create.contract_id,
            extract('year', Order.created_at) == year,
            extract('month', Order.created_at) == month,
        )
        existing_count = (await session.execute(count_stmt)).scalar() or 0
        seq = existing_count + 1

        short_customer = (contract.customer.short_name or "").strip() or "—"
        short_subject = (contract.short_subject or "").strip() or "—"
        short_order = (spec_order.short_name or "").strip() or "—"

        generated_number = (
            f"{obj.number_in_contract}/{month:02d}/{year:04d}/"
            f"{short_customer}/{short_subject}/{short_order}/{seq}"
        )

        # На случай гонки или ручных правок номеров — финальная проверка уникальности.
        if await order_data.check_order_number_exists(session, generated_number):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Не удалось сгенерировать уникальный номер заявки "
                    f"('{generated_number}' уже существует). Повторите попытку."
                )
            )

        order = await order_data.create_order(
            session,
            order_create,
            current_user.id,
            number=generated_number,
        )

        await log_activity(
            session, current_user,
            action='create', entity='order', entity_id=order.id,
            summary=f'Создал заявку №{order.number}',
        )
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
        existing = await order_data.get_order_by_id(session, order_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Заявка с id {order_id} не найдена"
            )
        
        # Ограничение «менять только свои заявки» снято 2026-08-27:
        # у роли уже есть отдельный флаг order_modify, проверенный выше
        # через check_permission — этого достаточно. Параллельный
        # /api/order/bulk_assign с тем же RBAC работает по всем заявкам,
        # так что одиночный PATCH был единственным местом с рудиментом.

        # Проверка уникальности номера, если он меняется
        if order_update.number and order_update.number != existing.number:
            if await order_data.check_order_number_exists(session, order_update.number, order_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Заявка с номером '{order_update.number}' уже существует"
                )
        
        # Проверка существования связанных объектов, если они меняются
        update_data = order_update.model_dump(exclude_unset=True)
        
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

        # Ответственный: 0 → NULL (снять), > 0 → проверить что юзер существует.
        if 'assigned_to_id' in update_data:
            aid = update_data['assigned_to_id']
            if aid == 0 or aid is None:
                update_data['assigned_to_id'] = None
                order_update = order_update.model_copy(update={"assigned_to_id": None})
            elif not await order_data.check_user_exists(session, aid):
                raise HTTPException(
                    status_code=400,
                    detail=f"Пользователь с id {aid} не существует",
                )

        # Обновление
        order = await order_data.update_order(session, order_id, order_update)

        changed_keys = ', '.join(sorted(update_data.keys())) or 'нет полей'
        await log_activity(
            session, current_user,
            action='update', entity='order', entity_id=order.id,
            summary=f'Изменил заявку №{order.number}: {changed_keys}',
            details=update_data,
        )
        return order

# ========== МАССОВОЕ НАЗНАЧЕНИЕ ОТВЕТСТВЕННОГО ==========

async def bulk_assign_responsible(
    *,
    order_ids: List[int],
    assigned_to_id: Optional[int],
    current_user: User,
) -> int:
    """Массово проставить (или снять) ответственного у заявок.

    - `assigned_to_id=None` или `0` → снять ответственного (SET NULL).
    - Иначе — проверяем что юзер существует, ставим FK.
    Один activity_log — «Массово назначил <name> на N заявок» (или «снял
    ответственного с N заявок»), с полным списком id в details.
    """
    await check_permission(current_user, "order_modify", "изменения заявок")

    target_id = None if not assigned_to_id else assigned_to_id

    async with new_session() as session:
        target_name = None
        if target_id is not None:
            if not await order_data.check_user_exists(session, target_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Пользователь с id {target_id} не существует",
                )
            target_user = await session.get(User, target_id)
            target_name = (
                getattr(target_user, "full_name", None)
                or getattr(target_user, "name", None)
                or f"ID {target_id}"
            )

        stmt = (
            sa_update(Order)
            .where(Order.id.in_(order_ids))
            .values(assigned_to_id=target_id)
        )
        result = await session.execute(stmt)
        updated = int(result.rowcount or 0)

        if updated:
            summary = (
                f'Массово назначил ответственного «{target_name}» на {updated} заявок'
                if target_id is not None
                else f'Массово снял ответственного с {updated} заявок'
            )
            await log_activity(
                session, current_user,
                action='update', entity='order', entity_id=None,
                summary=summary,
                details={
                    'order_ids': order_ids,
                    'assigned_to_id': target_id,
                },
            )

        await session.commit()
        return updated


# ========== ОБНОВЛЕНИЕ СТАТУСА ==========

async def update_order_status(
    order_id: int,
    status_id: int,
    current_user: User
) -> Order:
    """
    Обновить статус заявки — принимает FK id из spec_order_statuses.
    """
    await check_permission(current_user, "order_modify", "изменения статуса заявок")

    async with new_session() as session:
        # Проверяем существование и права
        existing = await order_data.get_order_by_id(session, order_id)
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

        old_status_id = existing.status_id
        order = await order_data.update_order_status(session, order_id, status_id)

        # status_name из свежего снапшота (JOIN Spec_Order_Status),
        # но property `status_name` может лениться — берём через relation.
        new_status_name = None
        try:
            new_status_name = order.spec_order_status.name if order.spec_order_status else None
        except Exception:
            pass
        await log_activity(
            session, current_user,
            action='change_status', entity='order', entity_id=order.id,
            summary=f'Сменил статус заявки №{order.number} → '
                    f'{new_status_name or f"id={status_id}"}',
            details={'old_status_id': old_status_id, 'new_status_id': status_id},
        )
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
        order = await order_data.get_order_by_id(
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
        order_number = order.number  # снапшот до удаления — для лога
        success = await order_data.delete_order(session, order_id)

        if success:
            await log_activity(
                session, current_user,
                action='delete', entity='order', entity_id=order_id,
                summary=f'Удалил заявку №{order_number}',
            )
        return success