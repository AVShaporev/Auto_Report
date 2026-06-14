import logging
from typing import Optional, List, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from model.contract import Contract
from model.object import Object
from model.user import User
from data import object as object_data
from schema.object import ObjectCreate, ObjectUpdate
from schema.pagination import PaginationParams
from database.database import new_session
from service.order_autogen import create_initial_orders_for_object


logger = logging.getLogger(__name__)

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
        permission: Название права (object_read, object_create и т.д.)
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

async def get_object_by_id(
    object_id: int,
    current_user: User,
    load_relations: bool = False
) -> Object:
    """
    Получить объект по ID с проверкой прав
    """
    await check_permission(current_user, "object_read", "просмотра объектов")
    
    async with new_session() as session:
        obj = await object_data.get_object_by_id(
            session, 
            object_id, 
            load_relations=load_relations
        )
        
        if not obj:
            raise HTTPException(
                status_code=404,
                detail=f"Объект с id {object_id} не найден"
            )
        
        return obj

async def get_objects_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    region_id: Optional[int] = None,
    arial_id: Optional[int] = None,
    locality_id: Optional[int] = None,
    street_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    executor_id: Optional[int] = None,
    period_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Object], int]:
    """
    Получить список объектов с пагинацией
    """
    await check_permission(current_user, "object_read", "просмотра списка объектов")

    async with new_session() as session:
        items, total = await object_data.get_object_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            region_id=region_id,
            arial_id=arial_id,
            locality_id=locality_id,
            street_id=street_id,
            contract_id=contract_id,
            customer_id=customer_id,
            executor_id=executor_id,
            period_id=period_id,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )

        return items, total

async def get_all_objects(
    current_user: User,
    load_relations: bool = False
) -> List[Object]:
    """
    Получить все объекты
    """
    await check_permission(current_user, "object_read", "просмотра объектов")
    
    async with new_session() as session:
        return await object_data.get_object_all(session, load_relations=load_relations)

async def get_object_options(
    current_user: User
) -> List[Object]:
    """
    Получить минимальную информацию об объектах для выпадающих списков
    """
    await check_permission(current_user, "object_read", "просмотра объектов")
    
    async with new_session() as session:
        return await object_data.get_object_options(session)

# ========== ПОЛУЧЕНИЕ СО СТАТИСТИКОЙ ==========

async def get_object_with_stats(
    object_id: int,
    current_user: User
) -> dict:
    """
    Получить объект со статистикой для ответа
    
    Возвращает словарь, готовый для сериализации в Pydantic схему
    """
    await check_permission(current_user, "object_read", "просмотра объектов")
    
    async with new_session() as session:
        # Получаем объект с загрузкой всех связанных данных
        obj = await object_data.get_object_by_id(
            session, 
            object_id,
            load_relations=True
        )
        
        if not obj:
            raise HTTPException(
                status_code=404,
                detail=f"Объект с id {object_id} не найден"
            )
        
        # Получаем статистику
        equipments_count = await object_data.count_object_equipments(session, object_id)
        reports_count = await object_data.count_object_reports(session, object_id)
        orders_count = await object_data.count_object_orders(session, object_id)
        
        # Формируем адрес для выпадающего списка
        address_parts = []
        if obj.locality:
            address_parts.append(obj.locality.name)
        if obj.street:
            address_parts.append(obj.street.name)
        if obj.build_number:
            address_parts.append(f"д.{obj.build_number}")
        if obj.room_number:
            address_parts.append(f"пом.{obj.room_number}")
        address = ", ".join(address_parts) if address_parts else None
        
        # Возвращаем готовый словарь для ответа
        return {
            "id": obj.id,
            "number_in_contract": obj.number_in_contract,
            "name": obj.name,
            "build_number": obj.build_number,
            "room_number": obj.room_number,
            "responsible_face": obj.responsible_face,
            "responsible_faces_contact": obj.responsible_faces_contact,
            "region_id": obj.region_id,
            "arial_id": obj.arial_id,
            "locality_id": obj.locality_id,
            "street_id": obj.street_id,
            "spec_build_id": obj.spec_build_id,
            "spec_room_id": obj.spec_room_id,
            "period_id": obj.period_id,
            "contract_id": obj.contract_id,
            "region_name": obj.region.name if obj.region else None,
            "arial_name": obj.arial.name if obj.arial else None,
            "locality_name": obj.locality.name if obj.locality else None,
            "street_name": obj.street.name if obj.street else None,
            "spec_build_name": obj.spec_build.name if obj.spec_build else None,
            "spec_room_name": obj.spec_room.name if obj.spec_room else None,
            "period_name": obj.period.name if obj.period else None,
            "contract_number": obj.contract.number if obj.contract else None,
            "equipments_count": equipments_count,
            "reports_count": reports_count,
            "orders_count": orders_count,
            "address": address
        }

async def get_objects_paginated_with_stats(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    region_id: Optional[int] = None,
    arial_id: Optional[int] = None,
    locality_id: Optional[int] = None,
    street_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    executor_id: Optional[int] = None,
    period_id: Optional[int] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[dict], int]:
    """
    Получить список объектов со статистикой для ответа
    """
    await check_permission(current_user, "object_read", "просмотра списка объектов")

    async with new_session() as session:
        # Получаем объекты с загрузкой связанных данных
        items, total = await object_data.get_object_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            region_id=region_id,
            arial_id=arial_id,
            locality_id=locality_id,
            street_id=street_id,
            contract_id=contract_id,
            customer_id=customer_id,
            executor_id=executor_id,
            period_id=period_id,
            sort_by=sort_by,
            sort_order=sort_order,
            load_relations=True
        )
        
        # Для каждого объекта получаем статистику и формируем краткий адрес
        result_items = []
        for item in items:
            equipments_count = await object_data.count_object_equipments(session, item.id)
            
            # Формируем адрес
            address_parts = []
            if item.locality:
                address_parts.append(item.locality.name)
            if item.street:
                address_parts.append(item.street.name)
            if item.build_number:
                address_parts.append(f"д.{item.build_number}")
            address = ", ".join(address_parts) if address_parts else None
            
            result_items.append({
                "id": item.id,
                "number_in_contract": item.number_in_contract,
                "name": item.name,
                "build_number": item.build_number,
                "room_number": item.room_number,
                "responsible_face": item.responsible_face,
                "region_name": item.region.name if item.region else None,
                "locality_name": item.locality.name if item.locality else None,
                "street_name": item.street.name if item.street else None,
                "contract_id": item.contract_id,
                "contract_number": item.contract.number if item.contract else None,
                "equipments_count": equipments_count,
                "address": address
            })
        
        return result_items, total

# ========== СОЗДАНИЕ ==========

async def create_object(
    object_create: ObjectCreate,
    current_user: User
) -> Object:
    """
    Создать новый объект
    """
    await check_permission(current_user, "object_create", "создания объектов")
    
    async with new_session() as session:
        # Проверка существования всех связанных объектов.
        # spec_room_id опционален — пропускаем проверку при None.
        checks = [
            (object_data.check_object_region_exists, object_create.region_id, "Регион"),
            (object_data.check_object_arial_exists, object_create.arial_id, "Район"),
            (object_data.check_object_locality_exists, object_create.locality_id, "Населенный пункт"),
            (object_data.check_object_street_exists, object_create.street_id, "Улица"),
            (object_data.check_object_spec_build_exists, object_create.spec_build_id, "Тип строения"),
            (object_data.check_object_period_exists, object_create.period_id, "Период"),
            (object_data.check_object_contract_exists, object_create.contract_id, "Контракт"),
        ]
        if object_create.spec_room_id is not None:
            checks.append(
                (object_data.check_object_spec_room_exists, object_create.spec_room_id, "Тип помещения"),
            )

        for check_func, entity_id, entity_name in checks:
            if not await check_func(session, entity_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"{entity_name} с id {entity_id} не существует"
                )
        
        # Создание
        obj = await object_data.create_object(session, object_create)

        # Авто-генерация заявок: «Первичное обследование» (всегда) и «Плановое ТО»
        # (если у периода объекта проставлен calendar code). См. service/order_autogen.
        # data.create_object уже committed → объект гарантированно сохранён.
        # Если автогенерация падает — логируем, но НЕ ломаем создание объекта:
        # пропущенные заявки админ создаст руками или их доберёт cron-tick.
        obj_id = obj.id  # снимок до возможного expire'а сессии
        try:
            stmt = (
                select(Object)
                .where(Object.id == obj_id)
                .options(
                    selectinload(Object.contract).selectinload(Contract.customer),
                    selectinload(Object.period),
                )
            )
            obj_for_autogen = (await session.execute(stmt)).scalar_one()
            await create_initial_orders_for_object(session, obj_for_autogen)
            await session.commit()
        except Exception:  # noqa: BLE001 — намеренно глотаем, не валим create_object
            await session.rollback()
            logger.exception(
                "Авто-генерация заявок для объекта id=%s упала — "
                "объект создан, заявки пропущены.",
                obj_id,
            )
            # rollback expires obj — refresh, иначе вызывающий API упадёт
            # MissingGreenlet при доступе к obj.id / obj.name после async-with.
            await session.refresh(obj)

        return obj

# ========== ОБНОВЛЕНИЕ ==========

async def update_object(
    object_id: int,
    object_update: ObjectUpdate,
    current_user: User
) -> Object:
    """
    Обновить объект
    """
    await check_permission(current_user, "object_modify", "изменения объектов")
    
    async with new_session() as session:
        # Проверяем существование
        existing = await object_data.get_object_by_id(session, object_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Объект с id {object_id} не найден"
            )
        
        # Проверка существования связанных объектов, если они меняются
        update_data = object_update.dict(exclude_unset=True)
        
        checks = [
            ('region_id', object_data.check_object_region_exists, "Регион"),
            ('arial_id', object_data.check_object_arial_exists, "Район"),
            ('locality_id', object_data.check_object_locality_exists, "Населенный пункт"),
            ('street_id', object_data.check_object_street_exists, "Улица"),
            ('spec_build_id', object_data.check_object_spec_build_exists, "Тип строения"),
            ('spec_room_id', object_data.check_object_spec_room_exists, "Тип помещения"),
            ('period_id', object_data.check_object_period_exists, "Период"),
            ('contract_id', object_data.check_object_contract_exists, "Контракт")
        ]
        
        for field, check_func, entity_name in checks:
            if field in update_data and update_data[field] != getattr(existing, field):
                # None допустим для опциональных полей (например, spec_room_id) —
                # проверять существование сущности не нужно, это просто сброс.
                if update_data[field] is None:
                    continue
                if not await check_func(session, update_data[field]):
                    raise HTTPException(
                        status_code=400,
                        detail=f"{entity_name} с id {update_data[field]} не существует"
                    )
        
        # Обновление
        obj = await object_data.update_object(session, object_id, object_update)
        
        return obj

# ========== УДАЛЕНИЕ ==========

async def delete_object(
    object_id: int,
    current_user: User
) -> bool:
    """
    Удалить объект
    """
    await check_permission(current_user, "object_delete", "удаления объектов")
    
    async with new_session() as session:
        # Проверяем существование и связанные объекты
        obj = await object_data.get_object_by_id(
            session, 
            object_id, 
            load_relations=True
        )
        
        if not obj:
            raise HTTPException(
                status_code=404,
                detail=f"Объект с id {object_id} не найден"
            )
        
        # Проверка на наличие связанных объектов
        if obj.objects_equipments and len(obj.objects_equipments) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить объект '{obj.name}': есть связанное оборудование ({len(obj.objects_equipments)} шт.)"
            )
        
        if obj.reports and len(obj.reports) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить объект '{obj.name}': есть связанные отчеты ({len(obj.reports)} шт.)"
            )
        
        if obj.orders and len(obj.orders) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить объект '{obj.name}': есть связанные заявки ({len(obj.orders)} шт.)"
            )
        
        # Удаление
        success = await object_data.delete_object(session, object_id)
        
        return success