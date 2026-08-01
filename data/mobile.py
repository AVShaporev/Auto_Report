"""Compact list-queries для mobile-клиента (Mobile M1.3).

Отдельный модуль, чтобы:
- mobile-специфичные запросы жили вместе — легко ревьюить перформанс;
- существующий data-слой не тратил лишние JOIN'ы для «обычных» endpoint'ов;
- entity-prefix naming: get_issues_mobile_list, get_objects_mobile_summary,
  get_reports_mobile_list, get_orders_mobile_list.

Философия: минимум колонок из основной сущности + строковое имя связи (без
загрузки full-object), без вложенных коллекций (attachments, equipment tree).
"""
from datetime import date
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from model.arial import Arial
from model.contract import Contract
from model.equipment import Equipment
from model.issue import Issue
from model.locality import Locality
from model.object import Object
from model.objects_equipment import Objects_Equipment
from model.order import Order
from model.report import Report
from model.role import Role
from model.spec_order import Spec_Order
from model.spec_priority import Spec_Priority
from model.spec_status import Spec_Status
from model.street import Street
from model.user import User


# ============================================================================
# Issues
# ============================================================================

async def get_issues_mobile_list(
    session: AsyncSession,
    *,
    user_id: int,
    only_open: bool = True,
    only_mine: bool = True,
    limit: int = 100,
) -> List[dict]:
    """Список неисправностей для mobile-инженера.

    По умолчанию — открытые, назначенные на меня. `only_mine=False` даёт
    все открытые (для прораба/руководителя).

    Возвращает dict'ы (не ORM-объекты) — сразу под MobileIssueListItem.
    """
    stmt = (
        select(
            Issue.id,
            Issue.number,
            Issue.title,
            Issue.is_critical,
            Issue.is_resolved,
            Issue.detected_date,
            Issue.resolved_date,
            Spec_Status.name.label("status_name"),
            Spec_Priority.code.label("priority_code"),
            Object.name.label("object_name"),
            Equipment.name.label("equipment_name"),
            User.full_name.label("assigned_to_name"),
        )
        .join(Spec_Status, Spec_Status.id == Issue.status_id)
        .join(Spec_Priority, Spec_Priority.id == Issue.priority_id)
        .join(Objects_Equipment, Objects_Equipment.id == Issue.object_equipment_id)
        .join(Object, Object.id == Objects_Equipment.object_id)
        .join(Equipment, Equipment.id == Objects_Equipment.equipment_id)
        .outerjoin(User, User.id == Issue.assigned_to_id)
    )
    if only_mine:
        stmt = stmt.where(Issue.assigned_to_id == user_id)
    if only_open:
        stmt = stmt.where(Issue.is_resolved.is_(False))
    stmt = stmt.order_by(
        Issue.is_critical.desc(),
        Issue.detected_date.desc(),
    ).limit(limit)

    rows = (await session.execute(stmt)).mappings().all()
    return [dict(r) for r in rows]


# ============================================================================
# Objects
# ============================================================================

async def get_objects_mobile_summary(
    session: AsyncSession,
    *,
    contract_id: Optional[int] = None,
    limit: int = 200,
) -> List[dict]:
    """Compact-список объектов + счётчики оборудования и открытых неисправностей.

    Один запрос — на объекты + subquery-count'ы (без загрузки самих коллекций).
    """
    # Sub-queries для counts: избегаем N+1.
    equipment_count = (
        select(func.count(Objects_Equipment.id))
        .where(Objects_Equipment.object_id == Object.id)
        .correlate(Object)
        .scalar_subquery()
    )
    open_issues_count = (
        select(func.count(Issue.id))
        .join(Objects_Equipment, Objects_Equipment.id == Issue.object_equipment_id)
        .where(Objects_Equipment.object_id == Object.id)
        .where(Issue.is_resolved.is_(False))
        .correlate(Object)
        .scalar_subquery()
    )

    stmt = (
        select(
            Object.id,
            Object.name,
            Object.build_number,
            Object.room_number,
            Object.number_in_contract,
            Contract.number.label("contract_number"),
            # Собираем короткий адрес прямо в SQL: locality + street.
            func.concat(
                Locality.name, ", ", Street.name,
            ).label("address_short"),
            equipment_count.label("equipment_count"),
            open_issues_count.label("open_issues_count"),
        )
        .join(Contract, Contract.id == Object.contract_id)
        .outerjoin(Locality, Locality.id == Object.locality_id)
        .outerjoin(Street, Street.id == Object.street_id)
    )
    if contract_id is not None:
        stmt = stmt.where(Object.contract_id == contract_id)
    stmt = stmt.order_by(Object.name).limit(limit)

    rows = (await session.execute(stmt)).mappings().all()
    return [dict(r) for r in rows]


# ============================================================================
# Reports
# ============================================================================

async def get_reports_mobile_list(
    session: AsyncSession,
    *,
    user_id: Optional[int] = None,
    only_mine: bool = True,
    limit: int = 100,
) -> List[dict]:
    """Список отчётов — мои (по умолчанию) или все."""
    stmt = (
        select(
            Report.id,
            Report.number,
            Report.created_at,
            Spec_Status.name.label("status_name"),
            Object.name.label("object_name"),
            User.full_name.label("author_name"),
        )
        .join(Spec_Status, Spec_Status.id == Report.status_id)
        .join(Object, Object.id == Report.object_id)
        .join(User, User.id == Report.user_id)
    )
    if only_mine and user_id is not None:
        stmt = stmt.where(Report.user_id == user_id)
    stmt = stmt.order_by(Report.created_at.desc()).limit(limit)

    rows = (await session.execute(stmt)).mappings().all()
    return [dict(r) for r in rows]


# ============================================================================
# Orders (плановые/аварийные заявки на ТО)
# ============================================================================

async def get_orders_mobile_list(
    session: AsyncSession,
    *,
    user_id: Optional[int] = None,
    only_mine: bool = True,
    only_open: bool = True,
    limit: int = 100,
) -> List[dict]:
    stmt = (
        select(
            Order.id,
            Order.number,
            Order.period_start_date,
            Order.created_at,
            Spec_Status.name.label("status_name"),
            Spec_Order.name.label("order_type"),
            Object.name.label("object_name"),
            User.full_name.label("assigned_to_name"),
        )
        .join(Spec_Status, Spec_Status.id == Order.status_id)
        .join(Spec_Order, Spec_Order.id == Order.spec_order_id)
        .join(Object, Object.id == Order.object_id)
        .outerjoin(User, User.id == Order.user_id)
    )
    if only_mine and user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)
    if only_open:
        # Открытыми считаем всё, что не done/cancelled. Точный enum статусов
        # не хардкодим — фильтруем по семантике имени.
        stmt = stmt.where(
            ~Spec_Status.name.ilike("%выполн%")
        )
    stmt = stmt.order_by(Order.created_at.desc()).limit(limit)

    rows = (await session.execute(stmt)).mappings().all()
    return [dict(r) for r in rows]
