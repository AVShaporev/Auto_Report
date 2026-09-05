"""Авто-генерация заявок (план — см. чат).

Три точки автоматического создания Order:

1. На создание объекта — заявка «Первичное обследование»
   (spec_order.is_default_primary = TRUE).
2. На создание объекта — первая «Плановая ТО» за текущий период
   обслуживания (spec_order.is_default_planned = TRUE),
   если у Period проставлен calendar code.
3. APScheduler tick в начале календарного периода (1-е число месяца/
   квартала/полугодия/года) — новая «Плановая» для каждого объекта.

Идемпотентность:
- Order.period_start_date проставляется только у авто-плановых.
- Partial UNIQUE(object_id, spec_order_id, period_start_date) WHERE
  period_start_date IS NOT NULL — БД сама ловит дубль.

Все функции принимают `session` извне → транзакционность контролирует
caller (create_object держит одну транзакцию вместе с авто-заявками;
tick на cron берёт по сессии на каждую заявку, чтобы один битый объект
не валил весь tick).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.database import new_session
from model.contract import Contract
from model.object import Object as ObjectModel
from model.order import Order
from model.organization import Organization
from model.period import Period
from model.spec_order import Spec_Order
from model.user import User


logger = logging.getLogger(__name__)


# Имя системного пользователя, от которого создаются авто-заявки.
# Создаётся миграцией e7c2a5d1f3b8 (is_protected=TRUE, is_active=FALSE).
SYSTEM_USER_NAME = "system"


# ========== РЕЗУЛЬТАТ TICK'А ==========

@dataclass
class TickResult:
    """Сводный отчёт по одному прогону tick_planned_orders."""
    objects_total: int = 0
    objects_skipped_no_period_code: int = 0
    objects_skipped_no_contract: int = 0
    orders_created: int = 0
    orders_already_exist: int = 0
    errors: list[str] = None  # noqa: RUF012  — мутируется по ходу

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    def summary(self) -> str:
        return (
            f"tick: всего объектов={self.objects_total}, "
            f"создано={self.orders_created}, уже есть={self.orders_already_exist}, "
            f"пропущено (нет period.code)={self.objects_skipped_no_period_code}, "
            f"пропущено (нет договора)={self.objects_skipped_no_contract}, "
            f"ошибок={len(self.errors)}"
        )


# ========== КАЛЕНДАРНЫЙ РАСЧЁТ ==========

def get_period_start(period_code: Optional[str], today: date) -> Optional[date]:
    """Начало текущего календарного периода для даты `today`.

    None / 'custom' → None (авто-tick игнорирует объекты с таким периодом).
    """
    if not period_code or period_code == "custom":
        return None

    if period_code == "monthly":
        return date(today.year, today.month, 1)

    if period_code == "quarterly":
        # 1-е января / апреля / июля / октября
        q_month = ((today.month - 1) // 3) * 3 + 1
        return date(today.year, q_month, 1)

    if period_code == "semiannual":
        # 1-е января / 1-е июля
        h_month = 1 if today.month <= 6 else 7
        return date(today.year, h_month, 1)

    if period_code == "yearly":
        return date(today.year, 1, 1)

    # Неизвестный код — лучше явно упасть, чем тихо пропустить (CHECK на
    # колонке должен был не дать таких записей появиться, но на всякий).
    raise ValueError(f"Неизвестный period.code: {period_code!r}")


# ========== ГЕНЕРАЦИЯ НОМЕРА ==========

def _sanitize_for_number(value: Optional[str]) -> str:
    """Убираем '/' из текстовых кусков номера, чтобы не разрушать формат.

    Пустые значения заменяем на '—' (m-dash), чтобы число слэшей в номере
    всегда было одинаковым.
    """
    if not value:
        return "—"
    return value.replace("/", "-").strip() or "—"


async def next_planned_order_number(
    session: AsyncSession,
    obj: ObjectModel,
    spec_order: Spec_Order,
    today: date,
) -> str:
    """Сгенерировать номер заявки по маске
    "<number_in_contract>/<MM>/<YYYY>/<customer.short_name>/<contract.short_subject>/<spec_order.short_name>/<seq>".

    `seq` — порядковый номер заявки для пары (object, spec_order):
    COUNT(orders WHERE object_id=X AND spec_order_id=Y) + 1. Per-type
    нумерация — иначе разные виды заявок дробят счётчик друг другу.

    `spec_order.short_name` подставляется как есть (с заменой '/' на '-');
    при пустом short_name берётся name, при пустом name — code.

    Требует, чтобы у `obj` была подгружена связь contract.customer.
    """
    contract: Optional[Contract] = obj.contract
    if contract is None:
        raise ValueError(
            f"Object id={obj.id} ({obj.name}) не имеет договора — "
            "автогенерация номера невозможна."
        )

    customer: Optional[Organization] = contract.customer

    customer_short = _sanitize_for_number(
        getattr(customer, "short_name", None) if customer else None
    )
    subject_short = _sanitize_for_number(contract.short_subject)
    spec_order_short = _sanitize_for_number(
        spec_order.short_name or spec_order.name or spec_order.code
    )

    count_q = select(func.count(Order.id)).where(
        Order.object_id == obj.id,
        Order.spec_order_id == spec_order.id,
    )
    seq = (await session.execute(count_q)).scalar_one() + 1

    return (
        f"{obj.number_in_contract}/"
        f"{today.month:02d}/{today.year}/"
        f"{customer_short}/{subject_short}/{spec_order_short}/{seq}"
    )


# ========== ЗАГРУЗКА КЛЮЧЕВЫХ СУЩНОСТЕЙ ==========

async def _get_system_user_id(session: AsyncSession) -> int:
    """ID юзера 'system'. Если его нет — миграция e7c2a5d1f3b8 не накатана."""
    r = await session.execute(
        select(User.id).where(User.name == SYSTEM_USER_NAME)
    )
    user_id = r.scalar_one_or_none()
    if user_id is None:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Системный пользователь '{SYSTEM_USER_NAME}' не найден. "
                "Накатайте миграцию e7c2a5d1f3b8."
            ),
        )
    return user_id


async def _get_default_spec_order(
    session: AsyncSession,
    *,
    planned: bool = False,
    primary: bool = False,
) -> Optional[Spec_Order]:
    """Найти spec_order с флагом is_default_planned или is_default_primary.

    Возвращает None, если админ не выбрал тип по умолчанию — caller'у
    решать, ронять или скипать.
    """
    if planned == primary:
        raise ValueError("Укажи ровно один из флагов planned/primary")

    flag_col = Spec_Order.is_default_planned if planned else Spec_Order.is_default_primary
    r = await session.execute(select(Spec_Order).where(flag_col.is_(True)))
    return r.scalar_one_or_none()


# ========== СОЗДАНИЕ ЗАЯВКИ ==========

async def _create_order(
    session: AsyncSession,
    *,
    obj: ObjectModel,
    spec_order: Spec_Order,
    system_user_id: int,
    today: date,
    period_start_date: Optional[date],
    description: Optional[str],
) -> Order:
    """Низкоуровневое создание Order. flush'ит, чтобы вытащить id и поймать
    UNIQUE-конфликт в пределах транзакции caller'а."""
    from data.spec_order_status import get_default_status_id
    from service.due_date import compute_due_date

    number = await next_planned_order_number(session, obj, spec_order, today)
    period_code = obj.period.code if obj.period else None
    due_date = compute_due_date(
        sla_kind=spec_order.sla_kind,
        sla_days=spec_order.sla_days,
        created_at=today,
        period_start_date=period_start_date,
        period_code=period_code,
        sla_days_workdays=spec_order.sla_days_workdays,
    )
    order = Order(
        number=number,
        spec_order_id=spec_order.id,
        contract_id=obj.contract_id,
        object_id=obj.id,
        user_id=system_user_id,
        created_at=today,
        description=description,
        status_id=await get_default_status_id(session),
        period_start_date=period_start_date,
        due_date=due_date,
    )
    session.add(order)
    await session.flush()
    return order


# ========== ВНЕШНИЕ ТОЧКИ ВХОДА ==========

async def create_initial_orders_for_object(
    session: AsyncSession,
    obj: ObjectModel,
    today: Optional[date] = None,
) -> list[Order]:
    """Авто-заявки при создании объекта: primary + (если у периода есть
    календарный код) первая planned за текущий период.

    Caller отвечает за commit/rollback всей транзакции.

    obj должен быть уже flush'нут (есть id, contract_id, period_id) и
    иметь selectinload связей contract.customer и period.
    """
    today = today or date.today()
    created: list[Order] = []

    system_user_id = await _get_system_user_id(session)

    # 1) Первичное обследование — создаём всегда.
    primary_spec = await _get_default_spec_order(session, primary=True)
    if primary_spec is None:
        logger.warning(
            "Нет spec_order с is_default_primary=TRUE — "
            "пропускаю авто-первичную заявку для объекта id=%s", obj.id
        )
    else:
        primary_order = await _create_order(
            session,
            obj=obj,
            spec_order=primary_spec,
            system_user_id=system_user_id,
            today=today,
            period_start_date=None,
            description="Авто: первичное обследование при создании объекта.",
        )
        created.append(primary_order)

    # 2) Плановая ТО — только если у периода есть календарный код.
    planned_spec = await _get_default_spec_order(session, planned=True)
    if planned_spec is None:
        logger.warning(
            "Нет spec_order с is_default_planned=TRUE — "
            "пропускаю авто-плановую заявку для объекта id=%s", obj.id
        )
        return created

    period_obj: Optional[Period] = obj.period
    period_start = get_period_start(
        getattr(period_obj, "code", None) if period_obj else None,
        today,
    )
    if period_start is None:
        # custom-период или None — авто-tick его не трогает, primary создан.
        return created

    planned_order = await _create_order(
        session,
        obj=obj,
        spec_order=planned_spec,
        system_user_id=system_user_id,
        today=today,
        period_start_date=period_start,
        description=(
            f"Авто: плановое ТО за период с {period_start.strftime('%d.%m.%Y')}."
        ),
    )
    created.append(planned_order)
    return created


async def tick_planned_orders(
    today: Optional[date] = None,
) -> TickResult:
    """Cron-tick: пройти по всем объектам, для каждого попытаться создать
    плановую заявку за период, в который попадает `today`.

    Идемпотентно благодаря partial UNIQUE на (object_id, spec_order_id,
    period_start_date). Ошибки на отдельных объектах НЕ валят tick целиком —
    собираются в TickResult.errors.

    Каждая попытка — своя session с автокоммитом / откатом, чтобы один
    битый объект не отравлял остальные.
    """
    today = today or date.today()
    result = TickResult()

    # Шаг 1: достаём конфиг — system_user + spec_order для planned.
    async with new_session() as session:
        try:
            system_user_id = await _get_system_user_id(session)
        except HTTPException as e:
            result.errors.append(f"system-user: {e.detail}")
            return result

        planned_spec = await _get_default_spec_order(session, planned=True)
        if planned_spec is None:
            result.errors.append(
                "В справочнике spec_orders нет записи с is_default_planned=TRUE. "
                "Tick не может создать ни одной плановой заявки."
            )
            return result
        planned_spec_id = planned_spec.id

    # Шаг 2: список id объектов с подгруженным period.code и contract.
    async with new_session() as session:
        ids_q = select(ObjectModel.id).order_by(ObjectModel.id)
        result.objects_total = len((await session.execute(ids_q)).scalars().all())
        object_ids = (await session.execute(ids_q)).scalars().all()

    # Шаг 3: на каждый объект — отдельная транзакция.
    for object_id in object_ids:
        try:
            await _tick_one_object(
                object_id=object_id,
                today=today,
                planned_spec_id=planned_spec_id,
                system_user_id=system_user_id,
                result=result,
            )
        except Exception as e:  # noqa: BLE001 — не валим tick из-за одного объекта
            result.errors.append(f"object_id={object_id}: {type(e).__name__}: {e}")
            logger.exception("Ошибка в tick по object_id=%s", object_id)

    return result


async def _tick_one_object(
    *,
    object_id: int,
    today: date,
    planned_spec_id: int,
    system_user_id: int,
    result: TickResult,
) -> None:
    """Создание плановой заявки для одного объекта (своя транзакция).

    Состояние tick'а копится в общий TickResult, не возвращается напрямую.
    """
    async with new_session() as session:
        # Грузим объект со всеми нужными связями.
        stmt = (
            select(ObjectModel)
            .where(ObjectModel.id == object_id)
            .options(
                selectinload(ObjectModel.period),
                selectinload(ObjectModel.contract).selectinload(Contract.customer),
            )
        )
        obj = (await session.execute(stmt)).scalar_one_or_none()
        if obj is None:
            return  # удалили между select и обработкой

        if obj.contract is None:
            result.objects_skipped_no_contract += 1
            return

        period_code = getattr(obj.period, "code", None) if obj.period else None
        period_start = get_period_start(period_code, today)
        if period_start is None:
            result.objects_skipped_no_period_code += 1
            return

        # Идемпотентность: дедуп по «есть ли уже плановая, чей period_start_date
        # попадает в текущий или более поздний период». `>=` вместо `==` чинит
        # кейс, когда админ меняет period.code объекта на более широкий
        # (monthly → quarterly → yearly): заявка с period_start_date=2026-06-01
        # должна считаться покрывающей и Q2 (period_start=2026-04-01),
        # и 2026-й год целиком. Без этого tick плодит дубль на каждую смену.
        exists_q = (
            select(Order.id)
            .where(
                Order.object_id == obj.id,
                Order.spec_order_id == planned_spec_id,
                Order.period_start_date >= period_start,
            )
            .limit(1)
        )
        if (await session.execute(exists_q)).scalar_one_or_none() is not None:
            result.orders_already_exist += 1
            return

        # spec_order загружаем по id (a не из cache) — selectinload не нужен
        # внутри _create_order. Грузим минимальный объект.
        planned_spec = await session.get(Spec_Order, planned_spec_id)
        try:
            await _create_order(
                session,
                obj=obj,
                spec_order=planned_spec,
                system_user_id=system_user_id,
                today=today,
                period_start_date=period_start,
                description=(
                    f"Авто: плановое ТО за период с {period_start.strftime('%d.%m.%Y')}."
                ),
            )
            await session.commit()
            result.orders_created += 1
        except IntegrityError:
            # Кто-то параллельно вставил эту же запись (UNIQUE ловит).
            await session.rollback()
            result.orders_already_exist += 1
