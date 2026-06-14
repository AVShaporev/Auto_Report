"""
Тесты для service/order_autogen — автогенерация заявок.

Покрывает:
- get_period_start: все коды + неизвестный + None/custom
- _sanitize_for_number: пустые/слэши
- next_planned_order_number: формат и порядковый seq
- create_initial_orders_for_object: primary всегда, planned зависит от period.code
- tick_planned_orders: первый прогон, идемпотентность, отсутствие default-spec_order

Тестовая БД создаётся через Base.metadata.create_all (без миграций), поэтому
partial UNIQUE-индексы из миграции в test-схеме отсутствуют. Идемпотентность
тика проверяется через SELECT-перед-INSERT (логика в коде).
"""

import pytest
import pytest_asyncio
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from model.contract import Contract
from model.object import Object as ObjectModel
from model.order import Order
from model.period import Period
from model.role import Role
from model.spec_order import Spec_Order
from model.user import User
from service.order_autogen import (
    SYSTEM_USER_NAME,
    _sanitize_for_number,
    create_initial_orders_for_object,
    get_period_start,
    next_planned_order_number,
    tick_planned_orders,
)


# ============ ХЕЛПЕРЫ ============

async def _load_object_for_autogen(session, object_id: int) -> ObjectModel:
    """Загрузить объект со всеми связями, нужными для autogen-функций."""
    stmt = (
        select(ObjectModel)
        .where(ObjectModel.id == object_id)
        .options(
            selectinload(ObjectModel.contract).selectinload(Contract.customer),
            selectinload(ObjectModel.period),
        )
    )
    return (await session.execute(stmt)).scalar_one()


async def _seed_default_spec_orders(session) -> dict:
    """Создать spec_orders для planned + primary с флагами is_default_*."""
    primary = Spec_Order(
        name="Первичное обследование",
        code="primary",
        is_system=True,
        is_default_primary=True,
    )
    planned = Spec_Order(
        name="Плановое ТО",
        code="planned",
        is_system=True,
        is_default_planned=True,
    )
    session.add_all([primary, planned])
    await session.commit()
    await session.refresh(primary)
    await session.refresh(planned)
    return {"primary": primary, "planned": planned}


async def _seed_system_user(session) -> User:
    """Создать роль 'Система' + юзера 'system' (минимальное соответствие
    миграции e7c2a5d1f3b8 в боевой схеме)."""
    role = Role(name="Система", is_protected=True)
    session.add(role)
    await session.commit()
    await session.refresh(role)

    user = User(
        name=SYSTEM_USER_NAME,
        full_name="Системный пользователь",
        # Любой непустой hash — реальный логин в тестах не нужен.
        hash="$2b$12$placeholderHashForTestSystemUserDoesNotMatter12345",
        role_id=role.id,
        is_active=False,
        is_protected=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _set_period_code(session, period_id: int, code: str) -> None:
    """Проставить period.code (фабрика по умолчанию его не задаёт)."""
    period = await session.get(Period, period_id)
    period.code = code
    await session.commit()


# ============ get_period_start (чистая функция, без БД) ============

def test_get_period_start_none_or_custom():
    assert get_period_start(None, date(2026, 6, 14)) is None
    assert get_period_start("custom", date(2026, 6, 14)) is None


def test_get_period_start_monthly():
    assert get_period_start("monthly", date(2026, 6, 14)) == date(2026, 6, 1)
    assert get_period_start("monthly", date(2026, 1, 31)) == date(2026, 1, 1)


def test_get_period_start_quarterly_all_quarters():
    assert get_period_start("quarterly", date(2026, 1, 15)) == date(2026, 1, 1)
    assert get_period_start("quarterly", date(2026, 5, 15)) == date(2026, 4, 1)
    assert get_period_start("quarterly", date(2026, 8, 30)) == date(2026, 7, 1)
    assert get_period_start("quarterly", date(2026, 12, 31)) == date(2026, 10, 1)


def test_get_period_start_semiannual():
    assert get_period_start("semiannual", date(2026, 1, 1)) == date(2026, 1, 1)
    assert get_period_start("semiannual", date(2026, 6, 30)) == date(2026, 1, 1)
    assert get_period_start("semiannual", date(2026, 7, 1)) == date(2026, 7, 1)
    assert get_period_start("semiannual", date(2026, 12, 31)) == date(2026, 7, 1)


def test_get_period_start_yearly():
    assert get_period_start("yearly", date(2026, 7, 14)) == date(2026, 1, 1)


def test_get_period_start_unknown_raises():
    with pytest.raises(ValueError):
        get_period_start("biennial", date(2026, 1, 1))


# ============ _sanitize_for_number (чистая функция) ============

def test_sanitize_empty_to_mdash():
    assert _sanitize_for_number(None) == "—"
    assert _sanitize_for_number("") == "—"
    assert _sanitize_for_number("   ") == "—"


def test_sanitize_keeps_normal_text():
    assert _sanitize_for_number("ООО Ромашка") == "ООО Ромашка"
    assert _sanitize_for_number("ТО АПС") == "ТО АПС"


def test_sanitize_replaces_slashes():
    assert _sanitize_for_number("ТО АПС/АПТ") == "ТО АПС-АПТ"
    assert _sanitize_for_number("a/b/c") == "a-b-c"


# ============ next_planned_order_number ============

async def test_number_format_first_order(db_session, reference_data):
    """Первая заявка для объекта — seq=1, формат корректный."""
    obj = await _load_object_for_autogen(db_session, reference_data["object"].id)
    number = await next_planned_order_number(db_session, obj, date(2026, 5, 15))
    assert number == "1/05/2026/Заказчик/ТО/1"


async def test_number_format_seq_increments(db_session, reference_data):
    """После создания одной заявки seq у следующей = 2."""
    await _seed_default_spec_orders(db_session)
    await _seed_system_user(db_session)
    await _set_period_code(db_session, reference_data["period"].id, "monthly")

    obj = await _load_object_for_autogen(db_session, reference_data["object"].id)

    # Используем create_initial — создаст primary + planned
    await create_initial_orders_for_object(db_session, obj, today=date(2026, 5, 15))
    await db_session.commit()

    # Теперь seq должен быть 3 (две заявки уже есть)
    number = await next_planned_order_number(db_session, obj, date(2026, 5, 15))
    assert number == "1/05/2026/Заказчик/ТО/3"


async def test_number_format_month_zero_padded(db_session, reference_data):
    """Январь → '01', а не '1'."""
    obj = await _load_object_for_autogen(db_session, reference_data["object"].id)
    number = await next_planned_order_number(db_session, obj, date(2026, 1, 5))
    assert number.startswith("1/01/2026/")


# ============ create_initial_orders_for_object ============

async def test_create_initial_primary_and_planned(db_session, reference_data):
    """С monthly-кодом — две заявки: primary + planned."""
    specs = await _seed_default_spec_orders(db_session)
    await _seed_system_user(db_session)
    await _set_period_code(db_session, reference_data["period"].id, "monthly")

    obj = await _load_object_for_autogen(db_session, reference_data["object"].id)

    created = await create_initial_orders_for_object(
        db_session, obj, today=date(2026, 5, 15)
    )
    await db_session.commit()

    assert len(created) == 2
    # Порядок: сначала primary, потом planned
    primary_order, planned_order = created
    assert primary_order.spec_order_id == specs["primary"].id
    assert primary_order.period_start_date is None
    assert planned_order.spec_order_id == specs["planned"].id
    assert planned_order.period_start_date == date(2026, 5, 1)
    # Юзер — system
    sys_user_id = (await db_session.execute(
        select(User.id).where(User.name == SYSTEM_USER_NAME)
    )).scalar_one()
    assert primary_order.user_id == sys_user_id
    assert planned_order.user_id == sys_user_id


async def test_create_initial_no_period_code_only_primary(db_session, reference_data):
    """period.code=NULL → только primary, planned пропускается."""
    specs = await _seed_default_spec_orders(db_session)
    await _seed_system_user(db_session)
    # period.code остаётся None

    obj = await _load_object_for_autogen(db_session, reference_data["object"].id)

    created = await create_initial_orders_for_object(
        db_session, obj, today=date(2026, 5, 15)
    )
    await db_session.commit()

    assert len(created) == 1
    assert created[0].spec_order_id == specs["primary"].id


async def test_create_initial_no_default_primary_skips_primary(
    db_session, reference_data
):
    """Если is_default_primary не выставлен — primary не создаётся,
    но planned всё равно создаётся (если есть default_planned)."""
    # Только planned, без primary-spec_order'а.
    planned = Spec_Order(name="План", code="planned", is_default_planned=True)
    db_session.add(planned)
    await db_session.commit()
    await _seed_system_user(db_session)
    await _set_period_code(db_session, reference_data["period"].id, "monthly")

    obj = await _load_object_for_autogen(db_session, reference_data["object"].id)
    created = await create_initial_orders_for_object(
        db_session, obj, today=date(2026, 5, 15)
    )
    await db_session.commit()

    assert len(created) == 1
    assert created[0].spec_order_id == planned.id
    assert created[0].period_start_date == date(2026, 5, 1)


# ============ tick_planned_orders ============

async def test_tick_creates_planned_for_object(db_session, reference_data):
    """Простой tick: один объект, monthly-период → одна планируемая заявка."""
    specs = await _seed_default_spec_orders(db_session)
    await _seed_system_user(db_session)
    await _set_period_code(db_session, reference_data["period"].id, "monthly")

    result = await tick_planned_orders(today=date(2026, 5, 15))

    assert result.errors == []
    assert result.orders_created == 1
    assert result.orders_already_exist == 0
    assert result.objects_total == 1

    # Проверяем, что в БД лежит заявка с правильным period_start_date.
    r = await db_session.execute(
        select(Order).where(Order.spec_order_id == specs["planned"].id)
    )
    orders = r.scalars().all()
    assert len(orders) == 1
    assert orders[0].period_start_date == date(2026, 5, 1)


async def test_tick_idempotent_second_run(db_session, reference_data):
    """Повторный tick в тот же день — 0 новых, 1 уже существует."""
    await _seed_default_spec_orders(db_session)
    await _seed_system_user(db_session)
    await _set_period_code(db_session, reference_data["period"].id, "monthly")

    today = date(2026, 5, 15)
    r1 = await tick_planned_orders(today=today)
    assert r1.orders_created == 1

    r2 = await tick_planned_orders(today=today)
    assert r2.orders_created == 0
    assert r2.orders_already_exist == 1


async def test_tick_new_month_creates_new_planned(db_session, reference_data):
    """Tick в новом месяце — создаёт новую планируемую заявку."""
    await _seed_default_spec_orders(db_session)
    await _seed_system_user(db_session)
    await _set_period_code(db_session, reference_data["period"].id, "monthly")

    r_may = await tick_planned_orders(today=date(2026, 5, 15))
    assert r_may.orders_created == 1

    r_jun = await tick_planned_orders(today=date(2026, 6, 1))
    assert r_jun.orders_created == 1
    assert r_jun.orders_already_exist == 0


async def test_tick_no_default_planned_returns_error(db_session, reference_data):
    """В spec_orders нет is_default_planned → tick молча сообщает ошибку,
    не валится."""
    # Только primary, без planned.
    primary = Spec_Order(name="Primary", code="primary", is_default_primary=True)
    db_session.add(primary)
    await db_session.commit()
    await _seed_system_user(db_session)
    await _set_period_code(db_session, reference_data["period"].id, "monthly")

    result = await tick_planned_orders(today=date(2026, 5, 15))
    assert result.orders_created == 0
    assert len(result.errors) == 1
    assert "is_default_planned" in result.errors[0]


async def test_tick_skip_object_with_custom_period(db_session, reference_data):
    """Если у периода code='custom' (или NULL) — tick его пропускает."""
    await _seed_default_spec_orders(db_session)
    await _seed_system_user(db_session)
    await _set_period_code(db_session, reference_data["period"].id, "custom")

    result = await tick_planned_orders(today=date(2026, 5, 15))
    assert result.orders_created == 0
    assert result.objects_skipped_no_period_code == 1


# ============ Интеграция с service.object.create_object через API ============
#
# Тесты ниже идут через POST /api/object/create — это покрывает интеграцию
# `service.object.create_object` → `create_initial_orders_for_object`.
# Сидируем дефолтные spec_orders + system-юзера в отдельных фикстурах
# (db_session работает до admin_token, который дёргает login через client —
# смешивать db_session-в-теле с client в одном тесте на Windows нельзя,
# см. tests/conftest.py docstring).


@pytest_asyncio.fixture
async def autogen_seed_full(db_session, reference_data) -> dict:
    """Полный сидинг для авто-генерации: default-spec_orders + юзер system +
    period.code='monthly'."""
    specs = await _seed_default_spec_orders(db_session)
    await _seed_system_user(db_session)
    await _set_period_code(db_session, reference_data["period"].id, "monthly")
    return {**reference_data, "default_spec_orders": specs}


def _build_object_payload(ref: dict, *, name: str) -> dict:
    """Минимальный JSON-body для POST /api/object/create."""
    return {
        "name": name,
        "responsible_face": "Сидоров",
        "responsible_faces_contact": "+70000000001",
        "region_id": ref["region"].id,
        "arial_id": ref["arial"].id,
        "locality_id": ref["locality"].id,
        "street_id": ref["street"].id,
        "spec_build_id": ref["spec_build"].id,
        "period_id": ref["period"].id,
        "contract_id": ref["contract"].id,
    }


async def test_api_create_object_triggers_autogen(
    client, autogen_seed_full, admin_token, auth_headers
):
    """POST /api/object/create → объект + две авто-заявки (primary + planned)."""
    payload = _build_object_payload(autogen_seed_full, name="Объект №2 (autogen)")
    resp = await client.post(
        "/api/object/create",
        json=payload,
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    new_object_id = resp.json()["id"]

    # Запрашиваем список заявок этого объекта через API (избегаем db_session
    # после client'а — Windows-asyncpg баг, см. conftest).
    list_resp = await client.get(
        f"/api/order/list?object_id={new_object_id}&per_page=10",
        headers=auth_headers(admin_token),
    )
    assert list_resp.status_code == 200, list_resp.text
    orders = list_resp.json()["items"]
    assert len(orders) == 2

    spec_codes = {o.get("spec_order_name") or "" for o in orders}
    assert any("Первичное" in name or "primary" in name.lower() for name in spec_codes)
    assert any("Плановое" in name or "planned" in name.lower() for name in spec_codes)


async def test_api_create_object_survives_autogen_failure(
    client, reference_data, admin_token, auth_headers
):
    """Если default-spec_orders + system-юзер не засидированы — объект
    всё равно создаётся (autogen падает, но не валит endpoint)."""
    # Сюда НЕ инжектим autogen_seed_full — данных для автогена нет.
    payload = _build_object_payload(reference_data, name="Объект №2 (no autogen)")
    resp = await client.post(
        "/api/object/create",
        json=payload,
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    new_object_id = resp.json()["id"]

    # У объекта не должно быть ни одной заявки.
    list_resp = await client.get(
        f"/api/order/list?object_id={new_object_id}&per_page=10",
        headers=auth_headers(admin_token),
    )
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["items"] == []
