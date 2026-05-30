"""
Доменные фабрики для тестов.

Принципы:
  - Каждая фабрика возвращает persistent объект (уже flush'нут в БД).
  - Все обязательные FK fields принимаются как kwargs или подставляются дефолтами
    через `bootstrap_minimum_reference_data` (вызывается фикстурой `reference_data`).
  - Никаких magic'ов с глобальным state — каждая фабрика получает свою `session`.
"""

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from model.role import Role
from model.user import User
from model.bank import Bank
from model.organization import Organization
from model.spec_region import Spec_Region
from model.region import Region
from model.spec_arial import Spec_Arial
from model.arial import Arial
from model.spec_locality import Spec_Locality
from model.locality import Locality
from model.spec_street import Spec_Street
from model.street import Street
from model.spec_build import Spec_Build
from model.spec_room import Spec_Room
from model.spec_job_title import Spec_Job_Title
from model.spec_contract import Spec_Contract
from model.spec_priority import Spec_Priority
from model.spec_status import Spec_Status
from model.spec_equipment import Spec_Equipment
from model.contract import Contract
from model.period import Period
from model.object import Object
from model.equipment import Equipment
from model.objects_equipment import Objects_Equipment
from model.issue import Issue
from service.auth import get_password_hash


# ============ ROLE / USER ============

# Все *_read/*_create/*_modify/*_delete флаги — формируются динамически,
# чтобы не таскать перечень из ~120 элементов вручную.
_PERMISSION_SUFFIXES = ("_read", "_create", "_modify", "_delete")


def _all_permission_flags() -> list[str]:
    """Все булевы поля Role с суффиксами *_read/*_create/*_modify/*_delete."""
    return [
        c.name
        for c in Role.__table__.columns
        if any(c.name.endswith(s) for s in _PERMISSION_SUFFIXES)
    ]


async def create_role(
    session: AsyncSession,
    *,
    name: str,
    is_admin: bool = False,
    is_superadmin: bool = False,
    grant_all: bool = False,
    grants: Optional[dict] = None,
) -> Role:
    """
    Создать роль.

    Args:
        grant_all: проставить True всем *_read/*_create/*_modify/*_delete (для admin/superadmin).
        grants: точечная карта {"object_read": True, ...} — приоритетнее grant_all.
    """
    payload = {"name": name, "is_admin": is_admin, "is_superadmin": is_superadmin}
    if grant_all:
        for f in _all_permission_flags():
            payload[f] = True
    if grants:
        payload.update(grants)
    role = Role(**payload)
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role


async def create_user(
    session: AsyncSession,
    *,
    name: str,
    password: str,
    role_id: int,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    is_active: bool = True,
) -> User:
    user = User(
        name=name,
        full_name=full_name or name,
        email=email or f"{name}@test.local",
        phone="+70000000000",
        telegram_id=f"tg_{name}",
        hash=get_password_hash(password),
        role_id=role_id,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ============ СПРАВОЧНИКИ-АТОМЫ ============

async def create_spec_priority(
    session: AsyncSession,
    *,
    name: str = "Средний",
    code: str = "medium",
) -> Spec_Priority:
    item = Spec_Priority(name=name, code=code)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def create_spec_status(
    session: AsyncSession,
    *,
    name: str = "Новая",
    code: str = "new",
) -> Spec_Status:
    item = Spec_Status(name=name, code=code)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


# ============ BOOTSTRAP МИНИМАЛЬНОГО НАБОРА ДАННЫХ ============

async def bootstrap_minimum_reference_data(session: AsyncSession) -> dict:
    """
    Создаёт минимальный комплект справочников + один объект + одно оборудование.

    Достаточно для тестов Issue / Order / Report, где требуются FK на всё подряд.
    Возвращает словарь с ключевыми объектами для повторного использования в тестах.
    """
    bank = Bank(name="Тестовый банк", bik="044525225", inn="7707083893")
    spec_region = Spec_Region(name="Область", description="ОБЛ")
    spec_arial = Spec_Arial(name="Городской округ", description="ГО")
    spec_locality = Spec_Locality(name="Город", short_name="г.")
    spec_street = Spec_Street(name="Улица", short_name="ул.")
    spec_build = Spec_Build(name="Здание")
    spec_room = Spec_Room(name="Помещение")
    spec_job_title = Spec_Job_Title(name="Директор")
    spec_contract = Spec_Contract(name="Госконтракт")
    spec_equipment = Spec_Equipment(name="Огнетушитель")

    priority_medium = Spec_Priority(name="Средний", code="medium")
    priority_high = Spec_Priority(name="Высокий", code="high")
    status_new = Spec_Status(name="Новая", code="new")
    status_resolved = Spec_Status(name="Устранена", code="resolved")

    period = Period(name="Месяц", period="monthly")

    session.add_all([
        bank, spec_region, spec_arial, spec_locality, spec_street,
        spec_build, spec_room, spec_job_title, spec_contract, spec_equipment,
        priority_medium, priority_high, status_new, status_resolved, period,
    ])
    await session.commit()

    region = Region(name="Тестовый регион", symbol="ТР", spec_region_id=spec_region.id)
    session.add(region)
    await session.commit()

    arial = Arial(name="Тестовый район", spec_arial_id=spec_arial.id)
    session.add(arial)
    await session.commit()

    locality = Locality(name="Тестгород", spec_locality_id=spec_locality.id)
    session.add(locality)
    await session.commit()

    street = Street(name="Тестовая", spec_street_id=spec_street.id)
    session.add(street)
    await session.commit()

    # Заказчик и подрядчик
    customer = Organization(
        name="ООО Заказчик", short_name="Заказчик",
        inn="1111111111", kpp="111111111",
        director_first_name="Иван", drector_last_name="Иванов", drector_surname="Иванович",
        corr_check="30101810400000000225", acc_check="40702810100000000001",
        pers_check="40702810100000000002",
        customer=True, executor=False,
        bank_id=bank.id, region_id=region.id, arial_id=arial.id,
        locality_id=locality.id, street_id=street.id,
        spec_build_id=spec_build.id, spec_job_title_id=spec_job_title.id,
    )
    executor = Organization(
        name="ООО Подрядчик", short_name="Подрядчик",
        inn="2222222222", kpp="222222222",
        director_first_name="Пётр", drector_last_name="Петров", drector_surname="Петрович",
        corr_check="30101810400000000226", acc_check="40702810100000000003",
        pers_check="40702810100000000004",
        customer=False, executor=True,
        bank_id=bank.id, region_id=region.id, arial_id=arial.id,
        locality_id=locality.id, street_id=street.id,
        spec_build_id=spec_build.id, spec_job_title_id=spec_job_title.id,
    )
    session.add_all([customer, executor])
    await session.commit()

    contract = Contract(
        number="К-001",
        date_of_consclusion=date(2026, 1, 1),
        date_of_completion=date(2026, 12, 31),
        summ=1_000_000.0,
        subject="ТО систем",
        short_subject="ТО",
        type_contract="государственный",
        spec_contract_id=spec_contract.id,
        customer_id=customer.id,
        executor_id=executor.id,
    )
    session.add(contract)
    await session.commit()

    obj = Object(
        name="Объект №1",
        responsible_face="Сидоров С.С.",
        responsible_faces_contact="+70000000000",
        region_id=region.id, arial_id=arial.id, locality_id=locality.id,
        street_id=street.id, spec_build_id=spec_build.id,
        period_id=period.id, contract_id=contract.id,
        number_in_contract=1,
    )
    session.add(obj)
    await session.commit()

    equipment = Equipment(
        name="Огнетушитель ОП-5",
        spec_equipment_id=spec_equipment.id,
    )
    session.add(equipment)
    await session.commit()

    objects_equipment = Objects_Equipment(
        object_id=obj.id, equipment_id=equipment.id, count=2,
    )
    session.add(objects_equipment)
    await session.commit()

    return {
        "bank": bank,
        "spec_priority": {"medium": priority_medium, "high": priority_high},
        "spec_status": {"new": status_new, "resolved": status_resolved},
        "spec_region": spec_region,
        "spec_arial": spec_arial,
        "spec_locality": spec_locality,
        "spec_street": spec_street,
        "spec_build": spec_build,
        "spec_room": spec_room,
        "spec_job_title": spec_job_title,
        "spec_contract": spec_contract,
        "spec_equipment": spec_equipment,
        "region": region,
        "arial": arial,
        "locality": locality,
        "street": street,
        "period": period,
        "customer": customer,
        "executor": executor,
        "contract": contract,
        "object": obj,
        "equipment": equipment,
        "objects_equipment": objects_equipment,
    }


# ============ ISSUE FACTORY ============

async def create_issue(
    session: AsyncSession,
    *,
    object_equipment_id: int,
    priority_id: int,
    status_id: int,
    reported_by_id: int,
    title: str = "Тестовая неисправность",
    number: str = "Н-0001",
    detected_date: date = date(2026, 1, 15),
    description: Optional[str] = None,
    is_critical: bool = False,
    assigned_to_id: Optional[int] = None,
) -> Issue:
    issue = Issue(
        number=number,
        title=title,
        description=description,
        priority_id=priority_id,
        status_id=status_id,
        detected_date=detected_date,
        is_critical=is_critical,
        object_equipment_id=object_equipment_id,
        reported_by_id=reported_by_id,
        assigned_to_id=assigned_to_id,
    )
    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return issue
