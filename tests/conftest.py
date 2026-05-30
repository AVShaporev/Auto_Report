"""
Корневой conftest для API-тестов Auto_Report.

Стратегия:
  1. Переопределяем env (`DB_NAME`, `MEDIA_ROOT`) ДО первого импорта проекта,
     чтобы `pydantic-settings` подтянул именно тестовые значения.
  2. На уровне session — создаём схему в тестовой БД через `Base.metadata.create_all`
     (миграции Alembic в тестах не прогоняются: цель тестов — API/сервисы/данные,
     не миграционные сценарии; см. tests/README.md, раздел «Тестовая БД»).
  3. На уровне function — `TRUNCATE ... RESTART IDENTITY CASCADE` чистит данные
     между тестами, не пересоздавая схему. Это в 50-100 раз быстрее drop_all+create_all.
  4. `AsyncClient` (httpx) поднимается через `ASGITransport(app=app)` — без сети,
     прямой вызов ASGI-приложения в том же процессе.
"""

# === ШАГ 1. ENV OVERRIDE ДО ИМПОРТОВ ПРОЕКТА ===
# Любая правка `os.environ` после `from config import settings` уже не повлияет
# на pydantic-settings: настройки кэшируются при первом инстанцировании.
# Этот блок ОБЯЗАН быть первым исполняемым кодом в файле.
import os
import sys
from pathlib import Path

# На Windows дефолтный ProactorEventLoop виснет в teardown'е async-фикстур
# (IOCP не получает завершение от asyncpg). SelectorEventLoop работает.
if sys.platform == "win32":
    import asyncio as _asyncio
    _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())

# Имя тестовой БД. Можно переопределить через TEST_DB_NAME=...
_TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "autoreport_test")
os.environ["DB_NAME"] = _TEST_DB_NAME

# MEDIA_ROOT под временную папку — тесты не должны писать в боевую media/.
_TEST_MEDIA = Path(__file__).resolve().parent / "_media"
_TEST_MEDIA.mkdir(parents=True, exist_ok=True)
os.environ["MEDIA_ROOT"] = str(_TEST_MEDIA)

# === ШАГ 2. ИМПОРТЫ ПРОЕКТА (уже с тестовым env) ===
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# --- ПАТЧ create_async_engine: NullPool в тестах ---
# Дефолтный пул держит соединения, привязанные к event loop'у, в котором они
# были созданы. pytest-asyncio открывает свежий loop на каждый тест → reuse
# пулленного коннекта валится с "Future attached to a different loop".
# NullPool отключает пул совсем — каждое .connect() открывает свежее
# соединение в текущем loop'е, что и нужно для тестов.
import sqlalchemy.ext.asyncio as _sa_async
from sqlalchemy.pool import NullPool as _NullPool

_orig_create_async_engine = _sa_async.create_async_engine

def _create_async_engine_nullpool(*args, **kwargs):
    kwargs.setdefault("poolclass", _NullPool)
    # Отключаем prepared statement cache asyncpg — на Windows+Selector loop
    # она вызывает «another operation in progress» при последовательных
    # коммитах на одной сессии.
    connect_args = kwargs.setdefault("connect_args", {})
    connect_args.setdefault("statement_cache_size", 0)
    connect_args.setdefault("prepared_statement_cache_size", 0)
    return _orig_create_async_engine(*args, **kwargs)

_sa_async.create_async_engine = _create_async_engine_nullpool
# --- /ПАТЧ ---

# Импорт database сначала — иначе models не зарегистрируются в Base.metadata.
from database.database import Base, engine, async_session_maker

# Импортируем все модели, чтобы Base.metadata знал про все таблицы.
# (Простой `from model import *` не подойдёт — model/__init__.py может
# не экспортировать всё подряд.)
import model.role  # noqa: F401
import model.user  # noqa: F401
import model.bank  # noqa: F401
import model.organization  # noqa: F401
import model.spec_region  # noqa: F401
import model.region  # noqa: F401
import model.spec_arial  # noqa: F401
import model.arial  # noqa: F401
import model.spec_locality  # noqa: F401
import model.locality  # noqa: F401
import model.spec_street  # noqa: F401
import model.street  # noqa: F401
import model.spec_build  # noqa: F401
import model.spec_room  # noqa: F401
import model.spec_job_title  # noqa: F401
import model.spec_contract  # noqa: F401
import model.spec_equipment  # noqa: F401
import model.spec_system  # noqa: F401
import model.spec_order  # noqa: F401
import model.spec_status  # noqa: F401
import model.spec_priority  # noqa: F401
import model.contract  # noqa: F401
import model.sub_contract  # noqa: F401
import model.period  # noqa: F401
import model.object  # noqa: F401
import model.equipment  # noqa: F401
import model.objects_equipment  # noqa: F401
import model.operation  # noqa: F401
import model.order  # noqa: F401
import model.report  # noqa: F401
import model.report_attachment  # noqa: F401
import model.issue  # noqa: F401
import model.issue_attachment  # noqa: F401

from main import app  # noqa: E402

# Импортируем фабрики ПОСЛЕ моделей (они используют их).
from tests.factories import (  # noqa: E402
    bootstrap_minimum_reference_data,
    create_role,
    create_user,
)


# === ШАГ 3. EVENT LOOP & DB FIXTURES ===

def pytest_collection_modifyitems(items):
    """
    Принудительно ставим всем async-тестам loop_scope="session", чтобы они
    делили один event loop с фикстурами session-scope (engine, _setup_schema).
    Без этого asyncpg-соединения, открытые в session-loop, недоступны из
    function-loop'ов тестов — «attached to a different loop».
    """
    session_marker = pytest.mark.asyncio(loop_scope="session")
    for item in items:
        if asyncio.iscoroutinefunction(getattr(item, "function", None)):
            item.add_marker(session_marker)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_schema() -> AsyncGenerator[None, None]:
    """
    Один раз на сессию: убедиться что схема в тестовой БД соответствует моделям.

    drop_all + create_all даёт чистый слепок без зависимости от миграций.
    Если предпочитаете прогонять Alembic — см. README, раздел «Альтернатива:
    тесты на миграциях».
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # После завершения всех тестов схему оставляем — это упрощает дебаг
    # последнего падения. Полный drop при перезапуске прогона.


@pytest_asyncio.fixture(autouse=True)
async def _truncate_between_tests() -> AsyncGenerator[None, None]:
    """
    Между тестами обнуляем все таблицы через единственный TRUNCATE с CASCADE.

    RESTART IDENTITY сбрасывает sequence для всех id'шников — тесты могут
    смело ассертить `id == 1` для первого созданного объекта.

    После TRUNCATE делаем `engine.dispose()` — это закрывает все asyncpg
    background-таски, иначе на Windows IOCP они могут зависнуть в teardown'е
    следующего теста.
    """
    yield  # Чистим ПОСЛЕ теста, а не до — тогда последнее состояние видно
    #          в pgAdmin/psql при дебаге.
    table_names = ", ".join(
        f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
    )
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Прямая сессия к тестовой БД — для фабрик и прямых assertion на данные.

    Тесты по API чаще ходят через `client`, но если нужно проверить, что
    «после POST в БД лежит то-то» — берите эту фикстуру.
    """
    # На Windows asyncpg оставляет «висящие» background-таски после
    # предыдущих API-запросов в этом же loop'е. dispose() убирает все
    # checked-in соединения и убивает остатки, чтобы свежая сессия
    # получила чистый сокет.
    await engine.dispose()
    session = async_session_maker()
    try:
        yield session
    finally:
        try:
            await session.rollback()
        except Exception:
            pass
        await session.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    httpx-клиент поверх ASGI без сети.

    base_url задан, чтобы относительные URL вида `/api/auth/login` работали
    в тестах в том же виде, как во фронте.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# === ШАГ 4. ДОМЕННЫЕ ФИКСТУРЫ (роли/пользователи/токены) ===

@pytest_asyncio.fixture
async def reference_data(db_session: AsyncSession) -> dict:
    """
    Минимальный набор справочных записей — нужен почти каждому тесту,
    потому что Object/Contract/etc. ссылаются на справочники по FK.

    Возвращает словарь с id и объектами для повторного использования.
    """
    return await bootstrap_minimum_reference_data(db_session)


@pytest_asyncio.fixture
async def superadmin_user(db_session: AsyncSession) -> dict:
    """Суперадмин — обходит RBAC, для проверок «happy path»."""
    role = await create_role(
        db_session,
        name="superadmin",
        is_superadmin=True,
        # все *_read/create/modify/delete на True
        grant_all=True,
    )
    user = await create_user(
        db_session,
        name="superadmin",
        password="supersecret123",
        role_id=role.id,
    )
    return {"user": user, "role": role, "password": "supersecret123"}


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> dict:
    """Админ — все права на чтение/изменение, но не суперадмин."""
    role = await create_role(
        db_session,
        name="admin",
        is_admin=True,
        grant_all=True,
    )
    user = await create_user(
        db_session,
        name="admin",
        password="adminpass123",
        role_id=role.id,
    )
    return {"user": user, "role": role, "password": "adminpass123"}


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession) -> dict:
    """
    Обычный пользователь — никаких *_create/*_modify/*_delete.
    Чтения выставлены минимальные (нужны, чтобы /auth/me не падал на RBAC).
    """
    role = await create_role(
        db_session,
        name="employee",
        # без флагов — все права = False
    )
    user = await create_user(
        db_session,
        name="employee",
        password="userpass123",
        role_id=role.id,
    )
    return {"user": user, "role": role, "password": "userpass123"}


async def _login(client: AsyncClient, username: str, password: str) -> str:
    """Внутренний хелпер — обмен (login, password) на access_token."""
    resp = await client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def superadmin_token(client: AsyncClient, superadmin_user: dict) -> str:
    return await _login(client, superadmin_user["user"].name, superadmin_user["password"])


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user: dict) -> str:
    return await _login(client, admin_user["user"].name, admin_user["password"])


@pytest_asyncio.fixture
async def regular_token(client: AsyncClient, regular_user: dict) -> str:
    return await _login(client, regular_user["user"].name, regular_user["password"])


@pytest.fixture
def auth_headers():
    """Хелпер: token → Authorization-заголовки. Чистая функция, не async."""
    def _build(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}
    return _build
