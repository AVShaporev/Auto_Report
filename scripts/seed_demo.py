"""
scripts/seed_demo.py — наполнение демо-тенанта (demo.cool-doc.ru)
правдоподобными данными для публичной «примерки» сервиса.

Идея:
    Тенант ежесуточно восстанавливается из «золотого» дампа. Этот
    скрипт создаёт эталонное наполнение ОДИН РАЗ — после провижна
    demo-тенанта. Затем делается `pg_dump` → `demo-seed.sql.gz`,
    и дальше cron просто заливает дамп поверх.

Что создаёт:
    • 2 роли (не superadmin): «Администратор» и «Менеджер»
      с плоскими правами по чек-листу (см. ниже DEMO_ROLE_* dict'ы).
    • 2 юзера с этими ролями: admin/demo1234, manager/demo1234
      (креды публичные, показаны на лендинге).
    • Справочники (регионы, здания, спец-типы, банк, период, статусы,
      приоритеты, типы заявок) — с реалистичными русскими названиями,
      без префикса [MOCK] (в отличие от seed_mock.py).
    • 2 организации: заказчик + исполнитель.
    • ~10 договоров, ~30 объектов, ~40 оборудования, ~120 связок
      object-equipment, ~50 заявок разных статусов и типов, ~20
      отчётов, ~10 неисправностей.

Запуск (из корня Auto_Report на VDS, внутри backend-контейнера
demo-тенанта):
    docker exec backend-demo poetry run python scripts/seed_demo.py

Идемпотентен: повторный запуск не пересоздаёт существующие
записи (проверяется по name/number). Безопасно вызывать многократно.

Пароль для обоих юзеров хардкоден в DEMO_PASSWORD (не секрет —
это же демо-стенд, креды всё равно публичны на посадочной).
"""

import asyncio
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import model  # noqa: F401 — регистрирует все модели в Base.metadata
from config import MEDIA_PATH, MEDIA_TEMPLATES_PATH
from database.database import new_session
from model import (
    Arial, Bank, Contract, Equipment, Issue, Locality, Object,
    Objects_Equipment, Order, Organization, Period, Region, Report, Role,
    Spec_Arial, Spec_Build, Spec_Contract, Spec_Equipment, Spec_Job_Title,
    Spec_Locality, Spec_Order, Spec_Order_Status, Spec_Priority, Spec_Region,
    Spec_Report_Status, Spec_Status, Spec_Street, Spec_System, Street, User,
)
from model.spec_journal import Spec_Journal  # не re-export'нут в model/__init__.py
from service.auth import get_password_hash

# Корень проекта — для доступа к templates/seeds/. `__file__` = scripts/seed_demo.py,
# `.parent.parent` → корень репо.
REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_SEEDS_DIR = REPO_ROOT / 'templates' / 'seeds'


# =============================================================================
# Константы демо
# =============================================================================

DEMO_PASSWORD = "demo1234"  # публичный, лендинг подскажет

# Права роли «Администратор» на demo — полный CRUD, is_admin=True, но НЕ
# superadmin. Не может ломать protected-записи (сам superadmin, дефолтные
# роли), не имеет доступа к платёжкам и опасным системным операциям.
DEMO_ROLE_ADMIN_PERMS = dict(
    is_admin=True,
    is_superadmin=False,
    is_protected=True,        # чтобы демо-юзер не удалил роль
    user_onboard_mobile=True,
    # user + role: полный CRUD
    user_read=True, user_create=True, user_modify=True, user_delete=True,
    role_read=True, role_create=True, role_modify=True, role_delete=True,
    # адресная база — CRUD
    spec_region_read=True, spec_region_create=True, spec_region_modify=True, spec_region_delete=True,
    region_read=True, region_create=True, region_modify=True, region_delete=True,
    spec_arial_read=True, spec_arial_create=True, spec_arial_modify=True, spec_arial_delete=True,
    arial_read=True, arial_create=True, arial_modify=True, arial_delete=True,
    spec_locality_read=True, spec_locality_create=True, spec_locality_modify=True, spec_locality_delete=True,
    locality_read=True, locality_create=True, locality_modify=True, locality_delete=True,
    spec_street_read=True, spec_street_create=True, spec_street_modify=True, spec_street_delete=True,
    street_read=True, street_create=True, street_modify=True, street_delete=True,
    spec_build_read=True, spec_build_create=True, spec_build_modify=True, spec_build_delete=True,
    spec_room_read=True, spec_room_create=True, spec_room_modify=True, spec_room_delete=True,
    # финансовые справочники — CRUD
    bank_read=True, bank_create=True, bank_modify=True, bank_delete=True,
    organization_read=True, organization_create=True, organization_modify=True, organization_delete=True,
    # договоры — CRUD
    spec_contract_read=True, spec_contract_create=True, spec_contract_modify=True, spec_contract_delete=True,
    contract_read=True, contract_create=True, contract_modify=True, contract_delete=True,
    sub_contract_read=True, sub_contract_create=True, sub_contract_modify=True, sub_contract_delete=True,
    period_read=True, period_create=True, period_modify=True, period_delete=True,
    # оборудование — CRUD
    spec_equipment_read=True, spec_equipment_create=True, spec_equipment_modify=True, spec_equipment_delete=True,
    equipment_read=True, equipment_create=True, equipment_modify=True, equipment_delete=True,
    object_read=True, object_create=True, object_modify=True, object_delete=True,
    object_equipment_read=True, object_equipment_create=True, object_equipment_modify=True, object_equipment_delete=True,
    operation_read=True, operation_create=True, operation_modify=True, operation_delete=True,
    spec_job_title_read=True, spec_job_title_create=True, spec_job_title_modify=True, spec_job_title_delete=True,
    # заявки — CRUD
    spec_order_read=True, spec_order_create=True, spec_order_modify=True, spec_order_delete=True,
    spec_system_read=True, spec_system_create=True, spec_system_modify=True, spec_system_delete=True,
    order_read=True, order_create=True, order_modify=True, order_delete=True,
    # отчёты — CRUD
    report_read=True, report_create=True, report_modify=True, report_delete=True,
    # неисправности — CRUD
    issue_read=True, issue_create=True, issue_modify=True, issue_delete=True,
    # справочники статусов/приоритетов/журналов — CRUD
    spec_status_read=True, spec_status_create=True, spec_status_modify=True, spec_status_delete=True,
    spec_order_status_read=True, spec_order_status_create=True, spec_order_status_modify=True, spec_order_status_delete=True,
    spec_report_status_read=True, spec_report_status_create=True, spec_report_status_modify=True, spec_report_status_delete=True,
    spec_priority_read=True, spec_priority_create=True, spec_priority_modify=True, spec_priority_delete=True,
    spec_journal_read=True, spec_journal_create=True, spec_journal_modify=True, spec_journal_delete=True,
)

# Права роли «Менеджер» на demo — read по всей операционной базе (чтобы
# формы работали, выпадашки не пустые), create/modify по своим рабочим
# сущностям (order/report/issue). Ничего не удаляет. Не видит role, не
# редактирует справочники, не имеет доступа к admin.*.
DEMO_ROLE_MANAGER_PERMS = dict(
    is_admin=False,
    is_superadmin=False,
    is_protected=True,
    user_onboard_mobile=False,
    # видит коллег для назначения ответственных, но не редактирует
    user_read=True,
    # адресная база — только чтение (заполняется админом)
    spec_region_read=True, region_read=True,
    spec_arial_read=True, arial_read=True,
    spec_locality_read=True, locality_read=True,
    spec_street_read=True, street_read=True,
    spec_build_read=True,
    spec_room_read=True,
    # финансовые справочники — только чтение
    bank_read=True, organization_read=True,
    # договоры — только чтение
    spec_contract_read=True, contract_read=True, sub_contract_read=True,
    period_read=True,
    # оборудование — только чтение
    spec_equipment_read=True, equipment_read=True,
    object_read=True, object_equipment_read=True,
    operation_read=True, spec_job_title_read=True,
    # заявки — read + create + modify (основная работа)
    spec_order_read=True, spec_system_read=True,
    order_read=True, order_create=True, order_modify=True,
    # отчёты — read + create + modify
    report_read=True, report_create=True, report_modify=True,
    # неисправности — read + create + modify (фиксирует найденные проблемы)
    issue_read=True, issue_create=True, issue_modify=True,
    # справочники статусов — только чтение
    spec_status_read=True, spec_order_status_read=True,
    spec_report_status_read=True, spec_priority_read=True,
    spec_journal_read=True,
)


# Пулы реалистичных названий (частично из landing showcase — консистентно
# с тем, что видит посетитель на cool-doc.ru перед переходом на demo).
# Адресная база в MVP — по одной репрезентативной записи каждого справочника
# (см. seed_dictionaries): «г. Москва» / ЦАО / ул. Тверская. Расширим когда
# станет мало объектов на одном адресе.

OBJECT_TEMPLATES = [
    'ЦОД «Северный», зал 1',
    'ЦОД «Северный», зал 2',
    'ЦОД «Северный», зал 3',
    'Офис на Тверской, 5 этаж',
    'Офис на Тверской, 6 этаж',
    'Офис на Тверской, 7 этаж',
    'Заводоуправление №1',
    'Заводоуправление №2',
    'Склад №1, зона А',
    'Склад №2, зона Б',
    'Склад №3, компрессорная',
    'Склад №4, компрессорная',
    'Насосная станция №1',
    'Насосная станция №2',
    'Котельная центральная',
    'Котельная резервная',
    'Логистический центр «Восток»',
    'Логистический центр «Запад»',
    'Административный корпус',
    'Производственный цех №1',
    'Производственный цех №2',
    'Гараж (тёплый бокс)',
    'Автомойка',
    'КПП главный',
    'КПП резервный',
    'Магазин, торговый зал',
    'Магазин, склад',
    'Ресторан «Панорама»',
    'Кафе «Терраса»',
    'Гостиница, 1 этаж',
]

EQUIPMENT_TEMPLATES = [
    ('ИБП APC Symmetra 16 kVA',        'ИБП',              'Электроснабжение'),
    ('ИБП APC Smart-UPS 3000',         'ИБП',              'Электроснабжение'),
    ('Кондиционер Daikin FTXB35',      'Кондиционер',      'Кондиционирование'),
    ('Кондиционер Mitsubishi Electric','Кондиционер',      'Кондиционирование'),
    ('АВР щита ВРУ-2',                 'АВР',              'Электроснабжение'),
    ('Насос Grundfos MAGNA3',          'Насос',            'Водоснабжение'),
    ('Насос Wilo Yonos',               'Насос',            'Водоснабжение'),
    ('Генератор Cummins C110D5',       'Генератор',        'Электроснабжение'),
    ('Компрессор Atlas Copco GA-30',   'Компрессор',       'Пневматика'),
    ('Котёл газовый Baxi Luna Duo-Tec','Котёл',            'Отопление'),
    ('Тепловой узел', 'Тепловой узел', 'Отопление'),
    ('Пожарная сигнализация Bolid',    'Сигнализация',     'Безопасность'),
    ('Видеонаблюдение Hikvision',      'Видеонаблюдение',  'Безопасность'),
    ('СКУД PERCo',                     'СКУД',             'Безопасность'),
    ('Лифт OTIS 2000',                 'Лифт',             'Вертикальный транспорт'),
    ('Приточная установка Systemair',  'Вентиляция',       'Вентиляция'),
    ('Чиллер Carrier 30RB',            'Чиллер',           'Кондиционирование'),
    ('Дизель-генератор Volvo 250 кВт', 'Генератор',        'Электроснабжение'),
    ('Пожарный шкаф ПК-В',             'Пожаротушение',    'Безопасность'),
    ('Датчик протечки Neptun',         'Датчик',           'Безопасность'),
]

CONTRACT_SUBJECTS = [
    'Комплексное техническое обслуживание инженерных систем',
    'Плановое ТО системы вентиляции и кондиционирования',
    'ППР электросиловой части',
    'Обслуживание систем безопасности (СКУД, видеонаблюдение, ОПС)',
    'Обслуживание тепломеханического оборудования',
    'Обслуживание ИБП и резервных источников питания',
    'Плановое ТО котельного оборудования',
    'Обслуживание лифтового хозяйства',
    'ТО систем водоснабжения и водоотведения',
    'ТО системы пожарной безопасности',
]

CUSTOMER_DEMO = dict(
    name='ООО «Технопром»',
    short_name='Технопром',
    inn='7701234567', kpp='770101001',
    director_first_name='Игорь',
    drector_last_name='Смирнов',
    drector_surname='Александрович',
    corr_check='30101810400000000225',
    acc_check='40702810900000012345',
    pers_check='40702810900000067890',
    customer=True, executor=False,
)

EXECUTOR_DEMO = dict(
    name='ООО «Сервис-Про»',
    short_name='Сервис-Про',
    inn='7709876543', kpp='770901001',
    director_first_name='Александр',
    drector_last_name='Петров',
    drector_surname='Викторович',
    corr_check='30101810400000000226',
    acc_check='40702810900000098765',
    pers_check='40702810900000054321',
    customer=False, executor=True,
)

BANK_DEMO = dict(name='Сбербанк, Московский филиал', bik='044525225', inn='7707083893')

MANAGER_FULLNAMES = [
    ('Иванов И.И.',    'Иван Иванович Иванов'),
    ('Петров А.С.',    'Александр Сергеевич Петров'),
    ('Сидорова О.В.',  'Ольга Викторовна Сидорова'),
]


# =============================================================================
# Утилиты
# =============================================================================

async def _first(session: AsyncSession, model_cls, **filters):
    stmt = select(model_cls)
    for k, v in filters.items():
        stmt = stmt.where(getattr(model_cls, k) == v)
    return (await session.execute(stmt.limit(1))).scalar_one_or_none()


async def _count(session: AsyncSession, model_cls, **filters) -> int:
    stmt = select(func.count()).select_from(model_cls)
    for k, v in filters.items():
        stmt = stmt.where(getattr(model_cls, k) == v)
    return (await session.execute(stmt)).scalar_one()


async def _get_or_create(session: AsyncSession, model_cls, defaults=None, **filters):
    """Возвращает существующую запись или создаёт новую. Идемпотентно."""
    existing = await _first(session, model_cls, **filters)
    if existing:
        return existing
    kwargs = {**filters, **(defaults or {})}
    obj = model_cls(**kwargs)
    session.add(obj)
    await session.flush()
    return obj


def copy_seed_templates() -> int:
    """
    Копирует все .docx/.dotx из `templates/seeds/` в MEDIA_TEMPLATES_PATH,
    перезаписывая существующие — эталон должен быть строго тем, что в
    репе (в отличие от `scripts/seed_templates.py`, который skip'ает
    существующие, чтобы не сломать админские загрузки в prod).
    Возвращает количество скопированных файлов.
    """
    if not TEMPLATE_SEEDS_DIR.exists():
        print(f"  ▸ Шаблоны: {TEMPLATE_SEEDS_DIR} не существует — пропуск")
        return 0

    MEDIA_TEMPLATES_PATH.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in TEMPLATE_SEEDS_DIR.iterdir():
        if not src.is_file():
            continue
        if src.suffix.lower() not in {'.docx', '.dotx'}:
            continue
        dst = MEDIA_TEMPLATES_PATH / src.name
        shutil.copy2(src, dst)
        copied += 1
        print(f"      {src.name} → {dst.relative_to(MEDIA_PATH)}")
    print(f"  ▸ Шаблоны: скопировано {copied} файлов в {MEDIA_TEMPLATES_PATH}")
    return copied


# =============================================================================
# Роли и пользователи
# =============================================================================

async def seed_roles(session: AsyncSession) -> tuple[int, int]:
    print("  ▸ Роли: «Администратор» и «Менеджер»")

    admin_role = await _first(session, Role, name='Администратор')
    if admin_role is None:
        admin_role = Role(name='Администратор', **DEMO_ROLE_ADMIN_PERMS)
        session.add(admin_role)
        await session.flush()
        print(f"      создана роль id={admin_role.id}")
    else:
        # Обновляем флаги на случай если чек-лист поменялся между запусками
        for k, v in DEMO_ROLE_ADMIN_PERMS.items():
            setattr(admin_role, k, v)
        print(f"      обновлены флаги роли id={admin_role.id}")

    manager_role = await _first(session, Role, name='Менеджер')
    if manager_role is None:
        manager_role = Role(name='Менеджер', **DEMO_ROLE_MANAGER_PERMS)
        session.add(manager_role)
        await session.flush()
        print(f"      создана роль id={manager_role.id}")
    else:
        for k, v in DEMO_ROLE_MANAGER_PERMS.items():
            setattr(manager_role, k, v)
        print(f"      обновлены флаги роли id={manager_role.id}")

    await session.commit()
    return admin_role.id, manager_role.id


async def seed_users(session: AsyncSession, admin_role_id: int, manager_role_id: int) -> tuple[int, int]:
    print("  ▸ Пользователи: admin/demo1234, manager/demo1234")
    password_hash = get_password_hash(DEMO_PASSWORD)

    admin_user = await _first(session, User, name='admin')
    if admin_user is None:
        admin_user = User(
            name='admin', full_name='Демо-Администратор',
            email='admin@demo.cool-doc.ru',
            hash=password_hash, role_id=admin_role_id, is_active=True,
            is_protected=True,
        )
        session.add(admin_user)
        await session.flush()
        print(f"      создан admin id={admin_user.id}")
    else:
        admin_user.hash = password_hash
        admin_user.role_id = admin_role_id
        admin_user.is_active = True
        admin_user.is_protected = True
        print(f"      обновлён admin id={admin_user.id} (сброс пароля)")

    manager_user = await _first(session, User, name='manager')
    if manager_user is None:
        manager_user = User(
            name='manager', full_name='Демо-Менеджер',
            email='manager@demo.cool-doc.ru',
            hash=password_hash, role_id=manager_role_id, is_active=True,
            is_protected=True,
        )
        session.add(manager_user)
        await session.flush()
        print(f"      создан manager id={manager_user.id}")
    else:
        manager_user.hash = password_hash
        manager_user.role_id = manager_role_id
        manager_user.is_active = True
        manager_user.is_protected = True
        print(f"      обновлён manager id={manager_user.id} (сброс пароля)")

    await session.commit()
    return admin_user.id, manager_user.id


# =============================================================================
# Справочники
# =============================================================================

async def seed_dictionaries(session: AsyncSession) -> dict:
    print("  ▸ Справочники (регионы, здания, банк, статусы, приоритеты…)")
    ids = {}

    # Regions / arials / localities / streets — по одному репрезентативному
    spec_region = await _get_or_create(session, Spec_Region, name='Город')
    region = await _get_or_create(
        session, Region, name='г. Москва',
        defaults=dict(symbol='МСК', spec_region_id=spec_region.id),
    )
    ids['region_id'] = region.id

    spec_arial = await _get_or_create(session, Spec_Arial, name='Административный округ')
    arial = await _get_or_create(
        session, Arial, name='ЦАО',
        defaults=dict(spec_arial_id=spec_arial.id),
    )
    ids['arial_id'] = arial.id

    spec_locality = await _get_or_create(session, Spec_Locality, name='Город')
    locality = await _get_or_create(
        session, Locality, name='г. Москва',
        defaults=dict(spec_locality_id=spec_locality.id),
    )
    ids['locality_id'] = locality.id

    spec_street = await _get_or_create(
        session, Spec_Street, name='улица',
        defaults=dict(short_name='ул.'),
    )
    street = await _get_or_create(
        session, Street, name='ул. Тверская',
        defaults=dict(spec_street_id=spec_street.id),
    )
    ids['street_id'] = street.id

    spec_build = await _get_or_create(session, Spec_Build, name='Здание')
    ids['spec_build_id'] = spec_build.id

    period = await _get_or_create(
        session, Period, name='Ежемесячно',
        defaults=dict(period='Раз в месяц', code='monthly'),
    )
    ids['period_id'] = period.id

    spec_contract = await _get_or_create(session, Spec_Contract, name='Договор ТО')
    ids['spec_contract_id'] = spec_contract.id

    spec_job_title = await _get_or_create(session, Spec_Job_Title, name='Генеральный директор')
    ids['spec_job_title_id'] = spec_job_title.id

    bank = await _get_or_create(
        session, Bank, name=BANK_DEMO['name'],
        defaults=dict(bik=BANK_DEMO['bik'], inn=BANK_DEMO['inn']),
    )
    ids['bank_id'] = bank.id

    spec_equipment = await _get_or_create(session, Spec_Equipment, name='Инженерное оборудование')
    ids['spec_equipment_id'] = spec_equipment.id

    spec_system = await _get_or_create(session, Spec_System, name='Электроснабжение')
    ids['spec_system_id'] = spec_system.id

    # 4 типа заявок с шаблонами. Файлы кладёт copy_seed_templates(),
    # здесь только запись в БД с template_storage_path (относительно
    # MEDIA_ROOT, `render_docx.py` собирает абсолютный через MEDIA_PATH).
    #
    # ВАЖНО: Alembic-миграция f5d8a2c1e9b4 сидит 3 системных spec_orders
    # с code ∈ {emergency, primary, planned} и is_system=True. Ищем по
    # code (уникальный ключ), при находке обновляем name/short_name/
    # template_*/sla_*, is_system не трогаем.
    spec_order_defs = [
        # (name, short_name, code, template_filename, sla_kind, sla_days)
        ('Плановое ТО',        'ППР', 'planned',   'planned.dotx',     'periodic',      None),
        ('Обслуживание',       'ТО',  'maint',     'maintenance.docx', 'periodic',      None),
        ('Аварийная заявка',   'АВР', 'emergency', 'emergency.docx',   'from_creation', 3),
        ('Первичный осмотр',   'ПО',  'primary',   'primary.dotx',     'manual',        None),
    ]
    spec_order_ids: dict[str, int] = {}  # code → id, для seed_orders
    for name, short_name, code, tpl_file, sla_kind, sla_days in spec_order_defs:
        existing = await _first(session, Spec_Order, code=code)
        tpl_path = f'templates/{tpl_file}'
        if existing is None:
            so = Spec_Order(
                name=name, short_name=short_name, code=code,
                template_filename=tpl_file,
                template_storage_path=tpl_path,
                sla_kind=sla_kind,
                sla_days=sla_days,
            )
            session.add(so)
            await session.flush()
            spec_order_ids[code] = so.id
        else:
            # Существует (либо из Alembic-seed, либо от прошлого прогона).
            # Обновляем видимые поля, is_system оставляем.
            existing.name = name
            existing.short_name = short_name
            existing.template_filename = tpl_file
            existing.template_storage_path = tpl_path
            existing.sla_kind = sla_kind
            existing.sla_days = sla_days
            spec_order_ids[code] = existing.id
    # Первый (planned) — оставляем как «дефолтный» для мест где нужен один id
    ids['spec_order_id'] = spec_order_ids['planned']
    ids['spec_order_ids'] = spec_order_ids

    # 2 типа журналов с прикреплёнными шаблонами. Контекст журнала
    # (см. render_docx.py::_build_journal_context) — только object/
    # contract/customer/executor/today, без order.* и equipment_groups,
    # поэтому в шаблонах паспорт объекта + пустая таблица записей.
    spec_journal_defs = [
        # (name, short_name, code, template_filename)
        ('Журнал технического обслуживания', 'ЖТО', 'journal_maint',   'journal_maint.docx'),
        ('Журнал первичного осмотра',        'ЖПО', 'journal_primary', 'journal_primary.docx'),
    ]
    for name, short_name, code, tpl_file in spec_journal_defs:
        tpl_path = f'templates/{tpl_file}'
        existing = await _first(session, Spec_Journal, code=code)
        if existing is None:
            # Пробуем по name — на случай если запись создавалась ранее
            # без code (в v1.0.40 skipped, но подстрахуемся).
            existing = await _first(session, Spec_Journal, name=name)
        if existing is None:
            sj = Spec_Journal(
                name=name, short_name=short_name, code=code,
                template_filename=tpl_file,
                template_storage_path=tpl_path,
            )
            session.add(sj)
            await session.flush()
        else:
            existing.name = name
            existing.short_name = short_name
            existing.code = code
            existing.template_filename = tpl_file
            existing.template_storage_path = tpl_path

    spec_status = await _get_or_create(
        session, Spec_Status, name='Новая',
        defaults=dict(code='new'),
    )
    ids['spec_status_id'] = spec_status.id

    spec_priority = await _get_or_create(
        session, Spec_Priority, name='Средний',
        defaults=dict(code='medium'),
    )
    ids['spec_priority_id'] = spec_priority.id

    # Spec_Order_Status и Spec_Report_Status сидятся Alembic-миграцией
    # с ровно одной is_default=true строкой (partial unique index).
    # Берём эту дефолтную запись для Order.status_id / Report.status_id.
    default_order_status = await _first(session, Spec_Order_Status, is_default=True)
    if default_order_status is None:
        raise RuntimeError(
            'В spec_order_statuses нет is_default записи. Alembic-миграция '
            'a0b1c2d3e4f5 не применена или дефолт был снят.'
        )
    ids['spec_order_status_id'] = default_order_status.id

    default_report_status = await _first(session, Spec_Report_Status, is_default=True)
    if default_report_status is None:
        raise RuntimeError(
            'В spec_report_statuses нет is_default записи. Alembic-миграция '
            'f3a4b5c6d7e8 не применена или дефолт был снят.'
        )
    ids['spec_report_status_id'] = default_report_status.id

    await session.commit()
    return ids


# =============================================================================
# Организации, договоры, объекты, оборудование
# =============================================================================

async def seed_organizations(session: AsyncSession, dict_ids: dict) -> tuple[int, int]:
    print("  ▸ Организации: заказчик + исполнитель")
    common_fk = dict(
        bank_id=dict_ids['bank_id'],
        region_id=dict_ids['region_id'],
        arial_id=dict_ids['arial_id'],
        locality_id=dict_ids['locality_id'],
        street_id=dict_ids['street_id'],
        spec_build_id=dict_ids['spec_build_id'],
        spec_job_title_id=dict_ids['spec_job_title_id'],
    )
    customer = await _get_or_create(
        session, Organization, name=CUSTOMER_DEMO['name'],
        defaults={**CUSTOMER_DEMO, **common_fk},
    )
    executor = await _get_or_create(
        session, Organization, name=EXECUTOR_DEMO['name'],
        defaults={**EXECUTOR_DEMO, **common_fk},
    )
    await session.commit()
    return customer.id, executor.id


async def seed_contracts(session: AsyncSession, dict_ids: dict,
                         customer_id: int, executor_id: int, target: int = 10) -> list[int]:
    print(f"  ▸ Договоры: цель {target}")
    ids = []
    today = date.today()

    for i in range(target):
        number = f'Д-2026/{i + 1:03d}'
        c = await _first(session, Contract, number=number)
        if c is None:
            subject = CONTRACT_SUBJECTS[i % len(CONTRACT_SUBJECTS)]
            c = Contract(
                number=number,
                date_of_consclusion=today - timedelta(days=180 + i * 15),
                date_of_completion=today + timedelta(days=365 - i * 10),
                summ=1_000_000.0 + i * 250_000.0,
                subject=subject,
                short_subject=subject.split(',')[0][:60],
                type_contract='service',
                spec_contract_id=dict_ids['spec_contract_id'],
                customer_id=customer_id,
                executor_id=executor_id,
            )
            session.add(c)
            await session.flush()
        ids.append(c.id)
    await session.commit()
    return ids


async def seed_objects(session: AsyncSession, dict_ids: dict, contract_ids: list[int],
                       target: int = 30) -> list[int]:
    print(f"  ▸ Объекты: цель {target}")
    ids = []
    per_contract: dict[int, int] = {}
    for cid in contract_ids:
        per_contract[cid] = await _count(session, Object, contract_id=cid)

    for i in range(target):
        name = OBJECT_TEMPLATES[i % len(OBJECT_TEMPLATES)]
        # На повторных прогонах имя может уже быть — просто пропускаем
        existing = await _first(session, Object, name=name)
        if existing:
            ids.append(existing.id)
            continue
        cid = contract_ids[i % len(contract_ids)]
        per_contract[cid] += 1
        manager_name = MANAGER_FULLNAMES[i % len(MANAGER_FULLNAMES)][1]
        o = Object(
            name=name,
            responsible_face=manager_name,
            responsible_faces_contact=f'+7 (495) 555-{(i + 100):04d}',
            region_id=dict_ids['region_id'],
            arial_id=dict_ids['arial_id'],
            locality_id=dict_ids['locality_id'],
            street_id=dict_ids['street_id'],
            spec_build_id=dict_ids['spec_build_id'],
            period_id=dict_ids['period_id'],
            contract_id=cid,
            number_in_contract=per_contract[cid],
        )
        session.add(o)
        await session.flush()
        ids.append(o.id)
    await session.commit()
    return ids


async def seed_equipment(session: AsyncSession, dict_ids: dict, target: int = 20) -> list[int]:
    """Каталог оборудования: 20 типов из EQUIPMENT_TEMPLATES."""
    print(f"  ▸ Оборудование (каталог): цель {target}")
    ids = []
    for i in range(target):
        name, _, _ = EQUIPMENT_TEMPLATES[i % len(EQUIPMENT_TEMPLATES)]
        e = await _first(session, Equipment, name=name)
        if e is None:
            e = Equipment(
                name=name,
                spec_equipment_id=dict_ids['spec_equipment_id'],
                spec_system_id=dict_ids['spec_system_id'],
            )
            session.add(e)
            await session.flush()
        ids.append(e.id)
    await session.commit()
    return ids


async def seed_objects_equipment(session: AsyncSession, dict_ids: dict,
                                 object_ids: list[int], equipment_ids: list[int]) -> int:
    """На каждый объект — 4 единицы разного оборудования (round-robin).
    UniqueConstraint(object_id, equipment_id) исключает дубли."""
    print("  ▸ Оборудование на объектах")
    today = date.today()
    added = 0
    for oi, oid in enumerate(object_ids):
        for slot in range(4):
            eid = equipment_ids[(oi * 4 + slot) % len(equipment_ids)]
            existing_stmt = select(Objects_Equipment).where(
                Objects_Equipment.object_id == oid,
                Objects_Equipment.equipment_id == eid,
            )
            existing = (await session.execute(existing_stmt)).scalar_one_or_none()
            if existing:
                continue
            inv_num = f'ИНВ-{oi + 1:03d}-{slot + 1}'
            oe = Objects_Equipment(
                count=1,
                inventory_number=inv_num,
                serial_number=f'SN-{oi + 1:03d}-{slot + 1}',
                installation_date=today - timedelta(days=60 + slot * 30),
                object_id=oid,
                equipment_id=eid,
                spec_system_id=dict_ids['spec_system_id'],
            )
            session.add(oe)
            added += 1
    await session.commit()
    print(f"      добавлено связок: {added}")
    return added


# =============================================================================
# Заявки, отчёты, неисправности
# =============================================================================

async def seed_orders(session: AsyncSession, dict_ids: dict, object_ids: list[int],
                      user_id: int, target: int = 50) -> int:
    """Заявки round-robin по 4 типам (planned/maint/emergency/primary) и по
    объектам. Номер несёт короткий префикс типа (ППР/ТО/АВР/ПО), чтобы в
    списке заявок сразу видно, что каталог типов работает."""
    print(f"  ▸ Заявки: цель {target}")
    obj_contract_stmt = select(Object.id, Object.contract_id).where(Object.id.in_(object_ids))
    pairs = [(r.id, r.contract_id) for r in (await session.execute(obj_contract_stmt)).all()]

    # (spec_order_id, prefix, description) в порядке округления
    order_types = [
        (dict_ids['spec_order_ids']['planned'],   'ППР', 'Плановое ТО по объекту, месяц {m}'),
        (dict_ids['spec_order_ids']['maint'],     'ТО',  'Обслуживание инженерных систем, месяц {m}'),
        (dict_ids['spec_order_ids']['emergency'], 'АВР', 'Аварийная заявка №{i}'),
        (dict_ids['spec_order_ids']['primary'],   'ПО',  'Первичный осмотр объекта'),
    ]

    added = 0
    for i in range(target):
        spec_order_id, prefix, desc_tpl = order_types[i % len(order_types)]
        # Локальный счётчик внутри типа для читаемого номера
        type_seq = i // len(order_types) + 1
        number = f'{prefix}-08/2026/{type_seq:03d}'
        existing = await _first(session, Order, number=number)
        if existing:
            continue
        oid, cid = pairs[i % len(pairs)]
        o = Order(
            number=number,
            spec_order_id=spec_order_id,
            contract_id=cid,
            object_id=oid,
            user_id=user_id,
            description=desc_tpl.format(m=(i % 12) + 1, i=type_seq),
            status_id=dict_ids['spec_order_status_id'],
        )
        session.add(o)
        added += 1
    await session.commit()
    print(f"      создано заявок: {added}")
    return added


async def seed_reports(session: AsyncSession, dict_ids: dict, object_ids: list[int],
                       user_id: int, target: int = 20) -> int:
    print(f"  ▸ Отчёты: цель {target}")
    obj_contract_stmt = select(Object.id, Object.contract_id).where(Object.id.in_(object_ids))
    pairs = [(r.id, r.contract_id) for r in (await session.execute(obj_contract_stmt)).all()]

    added = 0
    for i in range(target):
        number = f'ОТЧ-08/2026/{i + 1:03d}'
        existing = await _first(session, Report, number=number)
        if existing:
            continue
        oid, cid = pairs[i % len(pairs)]
        r = Report(
            number=number,
            status_id=dict_ids['spec_report_status_id'],
            period_id=dict_ids['period_id'],
            contract_id=cid,
            object_id=oid,
            user_id=user_id,
            description=f'Отчёт по проведённому ТО, объект #{i + 1}',
        )
        session.add(r)
        added += 1
    await session.commit()
    print(f"      создано отчётов: {added}")
    return added


async def seed_issues(session: AsyncSession, dict_ids: dict, user_id: int,
                      target: int = 10) -> int:
    print(f"  ▸ Неисправности: цель {target}")
    oe_stmt = select(Objects_Equipment.id).order_by(Objects_Equipment.id)
    oe_ids = [r for r in (await session.execute(oe_stmt)).scalars().all()]
    if not oe_ids:
        print("      пропуск: нет привязок object-equipment")
        return 0

    titles = [
        'Течь в системе водоснабжения',
        'Скачки напряжения на щите',
        'Кондиционер не выходит на режим',
        'Шум подшипника насоса',
        'Ошибка датчика протечки',
        'Нестабильная работа СКУД',
        'Пропадает связь с камерой видеонаблюдения',
        'Загрязнён фильтр приточной установки',
        'Требуется замена лампы аварийного освещения',
        'Не сработал АВР при отключении фидера',
    ]

    today = date.today()
    added = 0
    for i in range(target):
        number = f'НСР-08/2026/{i + 1:03d}'
        existing = await _first(session, Issue, number=number)
        if existing:
            continue
        title = titles[i % len(titles)]
        issue = Issue(
            number=number,
            title=title,
            description=f'{title}. Обнаружено при плановом обходе.',
            status_id=dict_ids['spec_status_id'],
            priority_id=dict_ids['spec_priority_id'],
            detected_date=today - timedelta(days=i % 20),
            object_equipment_id=oe_ids[i % len(oe_ids)],
            reported_by_id=user_id,
        )
        session.add(issue)
        added += 1
    await session.commit()
    print(f"      создано неисправностей: {added}")
    return added


# =============================================================================
# Главная
# =============================================================================

async def main():
    print("=" * 60)
    print("seed_demo — наполнение демо-тенанта cool-doc.ru")
    print("=" * 60)

    print("\n[1/7] Копирование .docx/.dotx шаблонов в MEDIA")
    copy_seed_templates()

    async with new_session() as session:
        print("\n[2/7] Роли и юзеры")
        admin_role_id, manager_role_id = await seed_roles(session)
        admin_user_id, manager_user_id = await seed_users(
            session, admin_role_id, manager_role_id
        )

        print("\n[3/7] Справочники (в т.ч. 4 spec_order с шаблонами)")
        dict_ids = await seed_dictionaries(session)

        print("\n[4/7] Организации + договоры + объекты")
        customer_id, executor_id = await seed_organizations(session, dict_ids)
        contract_ids = await seed_contracts(session, dict_ids, customer_id, executor_id, target=10)
        object_ids = await seed_objects(session, dict_ids, contract_ids, target=30)

        print("\n[5/7] Каталог оборудования и привязка к объектам")
        equipment_ids = await seed_equipment(session, dict_ids, target=20)
        await seed_objects_equipment(session, dict_ids, object_ids, equipment_ids)

        print("\n[6/7] Заявки (round-robin по 4 типам)")
        await seed_orders(session, dict_ids, object_ids, admin_user_id, target=50)

        print("\n[7/7] Отчёты + неисправности")
        await seed_reports(session, dict_ids, object_ids, admin_user_id, target=20)
        await seed_issues(session, dict_ids, admin_user_id, target=10)

    print("\n" + "=" * 60)
    print("✓ seed_demo завершён")
    print(f"  admin:   admin / {DEMO_PASSWORD}")
    print(f"  manager: manager / {DEMO_PASSWORD}")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
