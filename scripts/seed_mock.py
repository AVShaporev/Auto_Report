"""
scripts/seed_mock.py — массовая генерация моковских данных для perf-стресса.

Идемпотентен: все mock-записи помечены префиксом "[MOCK]" в name/number/etc.
Повторный запуск с теми же --target-N добивает до целевого N (или ничего
не делает, если N уже достигнут). Реальные (не-MOCK) записи не трогает.

Пример (на 192.168.1.8 stage из /opt/autoreport/stage/backend):
    poetry run python scripts/seed_mock.py \\
        --objects 200 --contracts 100 --equipment 1500 \\
        --orders 800 --reports 400 --issues 200

Дефолты соответствуют «Large»-варианту. Скрипт коммитит после каждого
большого батча (1000 записей), чтобы при падении посередине прогресс
сохранился и повторный запуск продолжил с того же места.

Префикс `[MOCK]` зашит в константу MOCK_PREFIX — поиск и зачистка:
    DELETE FROM issues WHERE number LIKE '[MOCK]%';
    DELETE FROM reports WHERE number LIKE '[MOCK]%';
    DELETE FROM orders WHERE number LIKE '[MOCK]%';
    DELETE FROM objects_equipments
        WHERE object_id IN (SELECT id FROM objects WHERE name LIKE '[MOCK]%');
    DELETE FROM objects WHERE name LIKE '[MOCK]%';
    DELETE FROM equipments WHERE name LIKE '[MOCK]%';
    DELETE FROM contracts WHERE number LIKE '[MOCK]%';
    -- ...справочники с [MOCK] аналогично, если нужно
"""

import argparse
import asyncio
import sys
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Регистрирует все модели в Base.metadata через side-effect импортов,
# иначе relationship'ы между ними не разрешаются (string-references).
import model  # noqa: F401
from database.database import new_session
from model import (
    Arial, Bank, Contract, Equipment, Issue, Locality, Object,
    Objects_Equipment, Order, Organization, Period, Region, Report, Role,
    Spec_Arial, Spec_Build, Spec_Contract, Spec_Equipment, Spec_Job_Title,
    Spec_Locality, Spec_Order, Spec_Priority, Spec_Region, Spec_Status,
    Spec_Street, Spec_System, Street, User,
)
from service.auth import get_password_hash

MOCK_PREFIX = "[MOCK]"


# ─────────────────────────────────────────────────────────────────────
# Утилиты
# ─────────────────────────────────────────────────────────────────────

async def _first(session: AsyncSession, model_cls, **filters):
    """Вернёт первую запись модели по фильтрам или None."""
    stmt = select(model_cls)
    for k, v in filters.items():
        stmt = stmt.where(getattr(model_cls, k) == v)
    return (await session.execute(stmt.limit(1))).scalar_one_or_none()


async def _count(session: AsyncSession, model_cls, **filters) -> int:
    """Сколько записей по фильтрам."""
    stmt = select(func.count()).select_from(model_cls)
    for k, v in filters.items():
        stmt = stmt.where(getattr(model_cls, k) == v)
    return (await session.execute(stmt)).scalar_one()


async def _count_mock(session: AsyncSession, model_cls, field: str = "name") -> int:
    """Сколько mock-записей (по префиксу в поле name/number)."""
    col = getattr(model_cls, field)
    stmt = select(func.count()).select_from(model_cls).where(col.like(f"{MOCK_PREFIX}%"))
    return (await session.execute(stmt)).scalar_one()


async def _all_ids_mock(session: AsyncSession, model_cls, field: str = "name") -> list[int]:
    """ID всех mock-записей (используется как пул для FK во вложенных сущностях)."""
    col = getattr(model_cls, field)
    stmt = select(model_cls.id).where(col.like(f"{MOCK_PREFIX}%")).order_by(model_cls.id)
    return [r for r in (await session.execute(stmt)).scalars().all()]


async def _any_id(session: AsyncSession, model_cls) -> int:
    """ID первой записи модели (для FK на не-mock справочники: spec_*, period, etc).

    Падает, если таблица пустая — это сигнал что нужный справочник
    не подготовлен ни системными seed'ами, ни нашим _ensure_mock_*.
    """
    stmt = select(model_cls.id).order_by(model_cls.id).limit(1)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise RuntimeError(f"Таблица {model_cls.__tablename__} пуста — нужен seed.")
    return row


# ─────────────────────────────────────────────────────────────────────
# Подготовка минимальных справочников
# ─────────────────────────────────────────────────────────────────────

async def ensure_dictionaries(session: AsyncSession) -> dict:
    """Гарантирует наличие минимально необходимых справочников.

    Возвращает словарь с id'шниками, которые потом используются в больших
    батчах (Contract, Object, Equipment, ...). Если справочник уже есть
    (системный seed, реальные данные) — переиспользуем первую запись;
    иначе создаём [MOCK]-версию.
    """
    print("  ▸ Справочники: проверяем и (если нужно) досаждаем минимальный набор")
    ids = {}

    # spec_region → region (Region.symbol тоже str_uniq)
    spec_region = await _first(session, Spec_Region) or Spec_Region(name=f"{MOCK_PREFIX} Тип региона")
    if spec_region.id is None:
        session.add(spec_region)
        await session.flush()
    region = await _first(session, Region) or Region(
        name=f"{MOCK_PREFIX} Регион", symbol=f"{MOCK_PREFIX[:6]}-1", spec_region_id=spec_region.id
    )
    if region.id is None:
        session.add(region)
        await session.flush()
    ids["region_id"] = region.id

    # spec_arial → arial
    spec_arial = await _first(session, Spec_Arial) or Spec_Arial(name=f"{MOCK_PREFIX} Тип района")
    if spec_arial.id is None:
        session.add(spec_arial)
        await session.flush()
    arial = await _first(session, Arial) or Arial(
        name=f"{MOCK_PREFIX} Район", spec_arial_id=spec_arial.id
    )
    if arial.id is None:
        session.add(arial)
        await session.flush()
    ids["arial_id"] = arial.id

    # spec_locality → locality
    spec_locality = await _first(session, Spec_Locality) or Spec_Locality(name=f"{MOCK_PREFIX} Тип нп")
    if spec_locality.id is None:
        session.add(spec_locality)
        await session.flush()
    locality = await _first(session, Locality) or Locality(
        name=f"{MOCK_PREFIX} Нас.пункт", spec_locality_id=spec_locality.id
    )
    if locality.id is None:
        session.add(locality)
        await session.flush()
    ids["locality_id"] = locality.id

    # spec_street → street (short_name required в Spec_Street)
    spec_street = await _first(session, Spec_Street) or Spec_Street(
        name=f"{MOCK_PREFIX} Тип улицы", short_name="mock"
    )
    if spec_street.id is None:
        session.add(spec_street)
        await session.flush()
    street = await _first(session, Street) or Street(
        name=f"{MOCK_PREFIX} Улица", spec_street_id=spec_street.id
    )
    if street.id is None:
        session.add(street)
        await session.flush()
    ids["street_id"] = street.id

    # spec_build (для objects.spec_build_id и organizations.spec_build_id)
    spec_build = await _first(session, Spec_Build) or Spec_Build(name=f"{MOCK_PREFIX} Тип строения")
    if spec_build.id is None:
        session.add(spec_build)
        await session.flush()
    ids["spec_build_id"] = spec_build.id

    # period с code (нужен для objects.period_id и reports.period_id)
    period = await _first(session, Period) or Period(
        name=f"{MOCK_PREFIX} Ежемесячно",
        period="Раз в месяц",
        code="monthly",
    )
    if period.id is None:
        session.add(period)
        await session.flush()
    ids["period_id"] = period.id

    # spec_contract (для contracts.spec_contract_id)
    spec_contract = await _first(session, Spec_Contract) or Spec_Contract(
        name=f"{MOCK_PREFIX} Тип контракта"
    )
    if spec_contract.id is None:
        session.add(spec_contract)
        await session.flush()
    ids["spec_contract_id"] = spec_contract.id

    # spec_job_title (для organizations)
    spec_job_title = await _first(session, Spec_Job_Title) or Spec_Job_Title(
        name=f"{MOCK_PREFIX} Должность"
    )
    if spec_job_title.id is None:
        session.add(spec_job_title)
        await session.flush()
    ids["spec_job_title_id"] = spec_job_title.id

    # bank (для organizations.bank_id)
    bank = await _first(session, Bank) or Bank(
        name=f"{MOCK_PREFIX} Банк", bik="044525000", inn="0000000000"
    )
    if bank.id is None:
        session.add(bank)
        await session.flush()
    ids["bank_id"] = bank.id

    # spec_equipment + spec_system (для equipments)
    spec_equipment = await _first(session, Spec_Equipment) or Spec_Equipment(
        name=f"{MOCK_PREFIX} Тип оборудования"
    )
    if spec_equipment.id is None:
        session.add(spec_equipment)
        await session.flush()
    ids["spec_equipment_id"] = spec_equipment.id

    spec_system = await _first(session, Spec_System) or Spec_System(
        name=f"{MOCK_PREFIX} Тип системы"
    )
    if spec_system.id is None:
        session.add(spec_system)
        await session.flush()
    ids["spec_system_id"] = spec_system.id

    # spec_order (для orders.spec_order_id)
    spec_order = await _first(session, Spec_Order) or Spec_Order(
        name=f"{MOCK_PREFIX} Плановая ТО"
    )
    if spec_order.id is None:
        session.add(spec_order)
        await session.flush()
    ids["spec_order_id"] = spec_order.id

    # spec_status + spec_priority (для issues и reports) — обязательны code+name
    spec_status = await _first(session, Spec_Status) or Spec_Status(
        name=f"{MOCK_PREFIX} Новая", code="mock_new"
    )
    if spec_status.id is None:
        session.add(spec_status)
        await session.flush()
    ids["spec_status_id"] = spec_status.id

    spec_priority = await _first(session, Spec_Priority) or Spec_Priority(
        name=f"{MOCK_PREFIX} Средний", code="mock_medium"
    )
    if spec_priority.id is None:
        session.add(spec_priority)
        await session.flush()
    ids["spec_priority_id"] = spec_priority.id

    await session.commit()
    return ids


async def ensure_mock_user(session: AsyncSession) -> int:
    """Mock-юзер для orders.user_id, reports.user_id, issues.reported_by_id.

    Не перезаписывает уже существующего seed_mock_user — берёт его как есть.
    Пароль — bcrypt-хеш от 'mock' (не нужен для perf-замера).
    """
    name = f"{MOCK_PREFIX} seed_user"
    existing = await _first(session, User, name=name)
    if existing:
        return existing.id

    role = await _first(session, Role)
    if role is None:
        raise RuntimeError("В БД нет ни одной роли — bootstrap не выполнен?")

    user = User(
        name=name,
        full_name=f"{MOCK_PREFIX} Mock User",
        hash=get_password_hash("mock"),
        role_id=role.id,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    return user.id


async def ensure_mock_organizations(session: AsyncSession, dict_ids: dict) -> tuple[int, int]:
    """Гарантирует наличие хотя бы одного [MOCK] customer и одного [MOCK] executor."""
    customer = await _first(session, Organization, name=f"{MOCK_PREFIX} Customer ООО")
    if customer is None:
        customer = Organization(
            name=f"{MOCK_PREFIX} Customer ООО",
            short_name=f"{MOCK_PREFIX} Customer",
            inn="7700000001",
            kpp="770001001",
            director_first_name="Иван",
            drector_last_name="Иванов",
            drector_surname="Иванович",
            corr_check="30101000000000000001",
            acc_check="40702000000000000001",
            pers_check="40702000000000000010",
            customer=True,
            executor=False,
            bank_id=dict_ids["bank_id"],
            region_id=dict_ids["region_id"],
            arial_id=dict_ids["arial_id"],
            locality_id=dict_ids["locality_id"],
            street_id=dict_ids["street_id"],
            spec_build_id=dict_ids["spec_build_id"],
            spec_job_title_id=dict_ids["spec_job_title_id"],
        )
        session.add(customer)
        await session.flush()

    executor = await _first(session, Organization, name=f"{MOCK_PREFIX} Executor ООО")
    if executor is None:
        executor = Organization(
            name=f"{MOCK_PREFIX} Executor ООО",
            short_name=f"{MOCK_PREFIX} Executor",
            inn="7700000002",
            kpp="770001002",
            director_first_name="Пётр",
            drector_last_name="Петров",
            drector_surname="Петрович",
            corr_check="30101000000000000002",
            acc_check="40702000000000000002",
            pers_check="40702000000000000020",
            customer=False,
            executor=True,
            bank_id=dict_ids["bank_id"],
            region_id=dict_ids["region_id"],
            arial_id=dict_ids["arial_id"],
            locality_id=dict_ids["locality_id"],
            street_id=dict_ids["street_id"],
            spec_build_id=dict_ids["spec_build_id"],
            spec_job_title_id=dict_ids["spec_job_title_id"],
        )
        session.add(executor)
        await session.flush()

    await session.commit()
    return customer.id, executor.id


# ─────────────────────────────────────────────────────────────────────
# Большие батчи
# ─────────────────────────────────────────────────────────────────────

BATCH_COMMIT_SIZE = 1000


async def _flush_if_needed(session: AsyncSession, added: int):
    """Коммитим раз в BATCH_COMMIT_SIZE — память не пухнет и при падении
    половина данных уже на диске."""
    if added and added % BATCH_COMMIT_SIZE == 0:
        await session.commit()


async def seed_contracts(session: AsyncSession, target: int, dict_ids: dict,
                         customer_id: int, executor_id: int) -> int:
    """Добивает [MOCK]-contracts до target. Возвращает финальное количество."""
    current = await _count_mock(session, Contract, "number")
    need = max(0, target - current)
    print(f"  ▸ Contracts: текущих [MOCK]={current}, нужно +{need} до {target}")
    if need == 0:
        return current

    today = date.today()
    for i in range(current, target):
        c = Contract(
            number=f"{MOCK_PREFIX}-CT-{i+1:05d}",
            date_of_consclusion=today - timedelta(days=365),
            date_of_completion=today + timedelta(days=365),
            summ=1_000_000.0,
            subject=f"{MOCK_PREFIX} Предмет контракта {i+1}",
            short_subject=f"{MOCK_PREFIX} Короткий {i+1}",
            type_contract="mock",
            spec_contract_id=dict_ids["spec_contract_id"],
            customer_id=customer_id,
            executor_id=executor_id,
        )
        session.add(c)
        await _flush_if_needed(session, i - current + 1)
    await session.commit()
    return target


async def seed_objects(session: AsyncSession, target: int, dict_ids: dict) -> int:
    """Добивает [MOCK]-objects до target. Распределяет round-robin по mock-contracts.

    number_in_contract инкрементируется на каждый contract отдельно — гарантия
    через UniqueConstraint(contract_id, number_in_contract).
    """
    current = await _count_mock(session, Object, "name")
    need = max(0, target - current)
    print(f"  ▸ Objects: текущих [MOCK]={current}, нужно +{need} до {target}")
    if need == 0:
        return current

    contract_ids = await _all_ids_mock(session, Contract, "number")
    if not contract_ids:
        raise RuntimeError("Нет mock-контрактов — сначала seed_contracts")

    # Считаем сколько уже объектов на каждый контракт (number_in_contract = их count+1+...)
    per_contract: dict[int, int] = {}
    for cid in contract_ids:
        per_contract[cid] = await _count(session, Object, contract_id=cid)

    for i in range(current, target):
        cid = contract_ids[i % len(contract_ids)]
        per_contract[cid] += 1
        o = Object(
            name=f"{MOCK_PREFIX} Object {i+1:05d}",
            responsible_face=f"{MOCK_PREFIX} Иванов И.И.",
            responsible_faces_contact=f"+7900000{(i % 10000):04d}",
            region_id=dict_ids["region_id"],
            arial_id=dict_ids["arial_id"],
            locality_id=dict_ids["locality_id"],
            street_id=dict_ids["street_id"],
            spec_build_id=dict_ids["spec_build_id"],
            period_id=dict_ids["period_id"],
            contract_id=cid,
            number_in_contract=per_contract[cid],
        )
        session.add(o)
        await _flush_if_needed(session, i - current + 1)
    await session.commit()
    return target


async def seed_equipment(session: AsyncSession, target: int, dict_ids: dict) -> int:
    """Добивает [MOCK]-equipment до target. Каждое — один общий spec_equipment."""
    current = await _count_mock(session, Equipment, "name")
    need = max(0, target - current)
    print(f"  ▸ Equipment: текущих [MOCK]={current}, нужно +{need} до {target}")
    if need == 0:
        return current

    for i in range(current, target):
        e = Equipment(
            name=f"{MOCK_PREFIX} Equipment {i+1:05d}",
            spec_equipment_id=dict_ids["spec_equipment_id"],
            spec_system_id=dict_ids["spec_system_id"],
        )
        session.add(e)
        await _flush_if_needed(session, i - current + 1)
    await session.commit()
    return target


async def seed_objects_equipment(session: AsyncSession, dict_ids: dict) -> int:
    """Привязывает каждое mock-equipment к одному mock-object (round-robin).

    UniqueConstraint(object_id, equipment_id) — два связывания одного eq к одному
    object'у невозможны, но равномерное распределение исключает коллизии.
    """
    equipment_ids = await _all_ids_mock(session, Equipment, "name")
    object_ids = await _all_ids_mock(session, Object, "name")
    if not equipment_ids or not object_ids:
        print("  ▸ Objects_Equipment: пропуск (нет equipment или objects)")
        return 0

    # Считаем существующие mock-связки (по принадлежности к [MOCK]-объекту).
    existing = await _count(session, Objects_Equipment)  # все, без фильтра по mock
    # Аккуратнее: запросим связки именно с mock-объектами
    stmt = (
        select(func.count())
        .select_from(Objects_Equipment)
        .join(Object, Object.id == Objects_Equipment.object_id)
        .where(Object.name.like(f"{MOCK_PREFIX}%"))
    )
    existing_mock = (await session.execute(stmt)).scalar_one()
    target = len(equipment_ids)
    need = max(0, target - existing_mock)
    print(f"  ▸ Objects_Equipment: текущих с [MOCK]-object'ами={existing_mock}, "
          f"нужно +{need} до {target}")
    if need == 0:
        return existing_mock

    today = date.today()
    for i in range(existing_mock, target):
        oe = Objects_Equipment(
            count=1,
            inventory_number=f"INV-{i+1:05d}",
            serial_number=f"SER-{i+1:05d}",
            installation_date=today - timedelta(days=30),
            object_id=object_ids[i % len(object_ids)],
            equipment_id=equipment_ids[i],
            spec_system_id=dict_ids["spec_system_id"],
        )
        session.add(oe)
        await _flush_if_needed(session, i - existing_mock + 1)
    await session.commit()
    return target


async def seed_orders(session: AsyncSession, target: int, dict_ids: dict, user_id: int) -> int:
    """Добивает [MOCK]-orders до target. Распределяет по mock-objects/contracts."""
    current = await _count_mock(session, Order, "number")
    need = max(0, target - current)
    print(f"  ▸ Orders: текущих [MOCK]={current}, нужно +{need} до {target}")
    if need == 0:
        return current

    # Подготавливаем пул object→contract (orders требует и object_id, и contract_id)
    pair_stmt = (
        select(Object.id, Object.contract_id)
        .where(Object.name.like(f"{MOCK_PREFIX}%"))
        .order_by(Object.id)
    )
    pairs = [(r.id, r.contract_id) for r in (await session.execute(pair_stmt)).all()]
    if not pairs:
        raise RuntimeError("Нет mock-объектов — сначала seed_objects")

    for i in range(current, target):
        oid, cid = pairs[i % len(pairs)]
        o = Order(
            number=f"{MOCK_PREFIX}-ORD-{i+1:05d}",
            spec_order_id=dict_ids["spec_order_id"],
            contract_id=cid,
            object_id=oid,
            user_id=user_id,
            description=f"{MOCK_PREFIX} description {i+1}",
            status="new",
        )
        session.add(o)
        await _flush_if_needed(session, i - current + 1)
    await session.commit()
    return target


async def seed_reports(session: AsyncSession, target: int, dict_ids: dict, user_id: int) -> int:
    """Добивает [MOCK]-reports до target. Распределяет по mock-objects/contracts."""
    current = await _count_mock(session, Report, "number")
    need = max(0, target - current)
    print(f"  ▸ Reports: текущих [MOCK]={current}, нужно +{need} до {target}")
    if need == 0:
        return current

    pair_stmt = (
        select(Object.id, Object.contract_id)
        .where(Object.name.like(f"{MOCK_PREFIX}%"))
        .order_by(Object.id)
    )
    pairs = [(r.id, r.contract_id) for r in (await session.execute(pair_stmt)).all()]
    if not pairs:
        raise RuntimeError("Нет mock-объектов — сначала seed_objects")

    for i in range(current, target):
        oid, cid = pairs[i % len(pairs)]
        r = Report(
            number=f"{MOCK_PREFIX}-RPT-{i+1:05d}",
            status_id=dict_ids["spec_status_id"],
            period_id=dict_ids["period_id"],
            contract_id=cid,
            object_id=oid,
            user_id=user_id,
            description=f"{MOCK_PREFIX} report description {i+1}",
        )
        session.add(r)
        await _flush_if_needed(session, i - current + 1)
    await session.commit()
    return target


async def seed_issues(session: AsyncSession, target: int, dict_ids: dict, user_id: int) -> int:
    """Добивает [MOCK]-issues до target. Привязывает к mock objects_equipment."""
    current = await _count_mock(session, Issue, "number")
    need = max(0, target - current)
    print(f"  ▸ Issues: текущих [MOCK]={current}, нужно +{need} до {target}")
    if need == 0:
        return current

    oe_stmt = (
        select(Objects_Equipment.id)
        .join(Object, Object.id == Objects_Equipment.object_id)
        .where(Object.name.like(f"{MOCK_PREFIX}%"))
        .order_by(Objects_Equipment.id)
    )
    oe_ids = [r for r in (await session.execute(oe_stmt)).scalars().all()]
    if not oe_ids:
        raise RuntimeError("Нет mock objects_equipment — сначала seed_objects_equipment")

    today = date.today()
    for i in range(current, target):
        issue = Issue(
            number=f"{MOCK_PREFIX}-ISS-{i+1:05d}",
            title=f"{MOCK_PREFIX} title {i+1}",
            description=f"{MOCK_PREFIX} description {i+1}",
            status_id=dict_ids["spec_status_id"],
            priority_id=dict_ids["spec_priority_id"],
            detected_date=today - timedelta(days=i % 30),
            object_equipment_id=oe_ids[i % len(oe_ids)],
            reported_by_id=user_id,
        )
        session.add(issue)
        await _flush_if_needed(session, i - current + 1)
    await session.commit()
    return target


# ─────────────────────────────────────────────────────────────────────
# Главная
# ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contracts", type=int, default=100)
    parser.add_argument("--objects", type=int, default=200)
    parser.add_argument("--equipment", type=int, default=1500)
    parser.add_argument("--orders", type=int, default=800)
    parser.add_argument("--reports", type=int, default=400)
    parser.add_argument("--issues", type=int, default=200)
    args = parser.parse_args()

    print(f"seed_mock: targets contracts={args.contracts} objects={args.objects} "
          f"equipment={args.equipment} orders={args.orders} reports={args.reports} "
          f"issues={args.issues}")
    started = datetime.now()

    async with new_session() as session:
        print("\n[1/4] Минимальные справочники")
        dict_ids = await ensure_dictionaries(session)
        print(f"      dict_ids: {dict_ids}")

        print("\n[2/4] Mock user + organizations")
        user_id = await ensure_mock_user(session)
        customer_id, executor_id = await ensure_mock_organizations(session, dict_ids)
        print(f"      user_id={user_id}, customer_id={customer_id}, executor_id={executor_id}")

        print("\n[3/4] Контракты и объекты")
        await seed_contracts(session, args.contracts, dict_ids, customer_id, executor_id)
        await seed_objects(session, args.objects, dict_ids)

        print("\n[4/4] Оборудование, заявки, отчёты, неисправности")
        await seed_equipment(session, args.equipment, dict_ids)
        await seed_objects_equipment(session, dict_ids)
        await seed_orders(session, args.orders, dict_ids, user_id)
        await seed_reports(session, args.reports, dict_ids, user_id)
        await seed_issues(session, args.issues, dict_ids, user_id)

    elapsed = (datetime.now() - started).total_seconds()
    print(f"\n✓ seed_mock завершён за {elapsed:.1f} сек")


if __name__ == "__main__":
    asyncio.run(main())
