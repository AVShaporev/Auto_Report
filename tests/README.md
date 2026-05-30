# Auto_Report — API tests

Набор pytest-тестов для API. Стек: **pytest + pytest-asyncio + httpx (ASGITransport)
+ pytest-timeout**.

Тесты ходят прямо в ASGI-приложение (без сети), пишут и читают тестовую
PostgreSQL базу, между тестами таблицы чистятся `TRUNCATE ... CASCADE`.

**Текущий статус:** 45 тестов, все проходят на Windows 10 +
локальный PostgreSQL 16 (порт 5433) за ~1:45.

---

## TL;DR — как запустить

```bash
# 1) Один раз: создать пустую тестовую БД и роль
psql -h 127.0.0.1 -p 5433 -U postgres -c "CREATE ROLE autoreport LOGIN PASSWORD 'autoreport' CREATEDB;"
psql -h 127.0.0.1 -p 5433 -U postgres -c "CREATE DATABASE autoreport_test OWNER autoreport;"

# 2) Один раз: подтянуть dev-deps
poetry install --with dev

# 3) Запуск — параметры подключения передаём env-переменными,
#     чтобы боевой .env не трогать.
DB_HOST=127.0.0.1 DB_PORT=5433 DB_USER=autoreport DB_PASSWORD=autoreport \
TEST_DB_NAME=autoreport_test poetry run pytest

# PowerShell:
$env:DB_HOST="127.0.0.1"; $env:DB_PORT="5433"; $env:DB_USER="autoreport"
$env:DB_PASSWORD="autoreport"; $env:TEST_DB_NAME="autoreport_test"
poetry run pytest

# Полезное:
poetry run pytest -v                       # подробный вывод
poetry run pytest tests/test_auth.py       # один файл
poetry run pytest -k "rbac"                # по подстроке имени теста
poetry run pytest -x                       # стоп на первой ошибке
poetry run pytest --lf                     # повторить только упавшие в прошлый раз
poetry run pytest --timeout=30             # лимит на тест (если зависнет)
```

> **Важно:** боевой `.env` указывает на удалённый prod-сервер. Передавайте
> параметры тестовой БД через переменные окружения, а не правкой `.env` — это
> исключает риск случайно прогнать тесты по проду (а тесты дропают всю схему
> при старте).

Если что-то падает на старте — см. секцию [Troubleshooting](#troubleshooting).

---

## Подготовка тестовой БД

Тесты используют **отдельную** PostgreSQL базу, чтобы:
- не зависеть от состояния dev-данных,
- безопасно дропать схему между прогонами.

По умолчанию имя БД — `autoreport_test`. Остальные параметры (`DB_HOST`,
`DB_PORT`, `DB_USER`, `DB_PASSWORD`) берутся из `.env` рядом с `config.py`.

### Вариант A — локальный PostgreSQL (Windows, текущий setup)

PostgreSQL 16 как Windows-служба `postgresql-16` на порту **5433**:

```bash
# 1) Зайти суперюзером (psql.exe в C:\Program Files\PostgreSQL\16\bin):
psql -h 127.0.0.1 -p 5433 -U postgres

# 2) Создать роль autoreport (если ещё нет) и тестовую БД:
CREATE ROLE autoreport LOGIN PASSWORD 'autoreport' CREATEDB;
CREATE DATABASE autoreport_test OWNER autoreport;
GRANT ALL PRIVILEGES ON DATABASE autoreport_test TO autoreport;
\q
```

Если потерян пароль `postgres` — в репо есть одноразовый
`reset_pg_password.sh` (Git Bash от админа), который сбрасывает его на
`postgres` через временный `trust` в `pg_hba.conf`. После использования
скрипт удалите.

### Вариант B — Postgres локально (любая ОС)

```bash
psql -U postgres
CREATE DATABASE autoreport_test;
GRANT ALL PRIVILEGES ON DATABASE autoreport_test TO autoreport;
\q
```

### Вариант C — Docker

```bash
docker run -d --name autoreport-pg-test \
    -e POSTGRES_DB=autoreport_test \
    -e POSTGRES_USER=autoreport \
    -e POSTGRES_PASSWORD=autoreport \
    -p 5433:5432 \
    postgres:16

# при запуске тестов:
# DB_HOST=localhost DB_PORT=5433 ... poetry run pytest
```

### Переопределение имени тестовой БД

```bash
TEST_DB_NAME=my_test_db poetry run pytest
```

В `tests/conftest.py` имя берётся из `TEST_DB_NAME`, иначе `autoreport_test`.

### Не использую миграции — почему?

Тесты создают схему через `Base.metadata.create_all`. Это намеренно:
- быстрее (~100 мс vs многих секунд Alembic),
- не зависит от истории миграций (любая поломка миграций — отдельный класс
  ошибок, который должен ловиться отдельным тестом или CI-шагом),
- позволяет тестировать без Alembic-окружения вовсе.

Если нужны тесты, которые проверяют именно миграционные сценарии —
заведите их в отдельной директории (например, `tests_migrations/`) с
собственным conftest, который прогоняет `alembic upgrade head` вместо
`create_all`.

---

## Структура

```
tests/
├── README.md                <- этот файл
├── __init__.py
├── conftest.py              <- env-override, фикстуры, чистка БД
├── factories.py             <- доменные фабрики (Role/User/Bank/Org/...)
├── helpers.py               <- общие assertion-хелперы
├── test_smoke.py            <- приложение поднимается, /docs и /openapi.json работают
├── test_auth.py             <- /api/auth/login + /refresh + /me
├── test_rbac.py             <- проверки прав на горячих эндпоинтах
├── test_pagination.py       <- PaginatedResponse contract + лимиты
├── test_validation.py       <- 422 от Pydantic v2 (required, length, etc.)
├── test_users.py            <- /api/user/list — что role с флагами приходит
├── test_spec_priority.py    <- эталонный CRUD простого справочника
└── test_issue.py            <- сложная сущность: FK, PATCH /status, бизнес-правила
```

### conftest.py — что важно понимать

1. **Env override до импортов.** Тесты подменяют `DB_NAME=autoreport_test`
   и `MEDIA_ROOT=tests/_media` **до** того, как импортируется любой
   модуль проекта. Это критично — pydantic-settings кэширует значения при
   первом инстансе `Settings()`.
2. **Selector event loop policy на Windows.** Дефолтный `ProactorEventLoop`
   зависает в teardown'е async-фикстур (IOCP не получает завершение от
   asyncpg). `WindowsSelectorEventLoopPolicy` устанавливается в самом
   начале conftest и решает проблему.
3. **NullPool для async-engine.** `create_async_engine` патчится перед
   импортом проекта — устанавливается `poolclass=NullPool`. Без этого
   соединения asyncpg остаются привязанными к loop'у, в котором были
   созданы, и сыпятся `Future attached to a different loop` при cross-loop
   использовании.
4. **Один loop на всю сессию тестов.** `pytest_collection_modifyitems`
   навешивает `@pytest.mark.asyncio(loop_scope="session")` на все
   async-тесты, чтобы они делили loop с session-scope фикстурой
   `_setup_schema`.
5. **Чистка через TRUNCATE.** Между тестами — один SQL вместо drop_all+create_all.
   `RESTART IDENTITY` даёт чистые id'шники, можно ассертить `== 1`.

### ⚠ Ограничение `db_session` после API-вызова (Windows + asyncpg)

Если в одном тесте сначала идёт HTTP-вызов через `client` (включая фикстуру
`superadmin_token` — она дёргает login), а **потом** в теле теста
используется прямая запись через `db_session` — asyncpg падает с
`InterfaceError: cannot perform operation: another operation is in progress`.
Происходит только на Windows.

**Безопасные паттерны:**

- `db_session` в фикстурах (до `client`) — ОК. Пример: `reference_data`,
  `superadmin_user` создают данные через `db_session`, и это работает.
- `db_session` в теле теста, без `client` фикстуры — ОК.
- В теле теста после login — создавать данные через API, не через
  `db_session` (см. `test_pagination.py::_seed_priorities` как пример).

Хочется иметь оба — `db_session` И `client` в одном тесте — пишите так:
сначала создайте всё через `db_session`, потом обращайтесь к `client`.
Обратный порядок ломается.

### Доступные фикстуры

| Фикстура | Что даёт |
|---|---|
| `client` | `httpx.AsyncClient` с ASGI-транспортом, `base_url="http://testserver"` |
| `db_session` | прямой `AsyncSession` для фабрик и проверки данных в БД |
| `auth_headers` | синхронная функция `(token) -> {"Authorization": "Bearer <t>"}` |
| `superadmin_user` / `superadmin_token` | пользователь с `is_superadmin=True` |
| `admin_user` / `admin_token` | пользователь с `is_admin=True` + все права |
| `regular_user` / `regular_token` | пользователь без прав (для тестов 403) |
| `reference_data` | минимум справочников + объект + оборудование. Используется для Issue/Order/Report тестов. Возвращает dict с ORM-объектами. |

---

## Как добавлять тесты для новой сущности

Шаблон CRUD-теста — `tests/test_spec_priority.py`. Скопируйте, поменяйте URL и payload.

Если сущность сложнее (есть FK на другие записи):

1. Добавьте фабрику в `tests/factories.py` (по образцу `create_issue`).
2. Используйте фикстуру `reference_data` — она уже создаёт цепочку
   Organization → Contract → Object → Equipment → Objects_Equipment +
   справочники приоритетов и статусов.
3. Если нужно — расширьте `bootstrap_minimum_reference_data` (но
   не раздувайте: каждое добавление замедляет ВСЕ тесты использующие фикстуру).

### Чек-лист «хороший тест для эндпоинта»

- [ ] **Happy path** — payload валиден, ответ 200/201, тело соответствует схеме.
- [ ] **RBAC 403** — обычный пользователь без `*_create/_modify/_delete` получает 403.
- [ ] **Auth 401** — без токена или с битым токеном → 401/403.
- [ ] **Validation 422** — отсутствует обязательное поле / превышен max_length.
- [ ] **Not found 404** — для `GET /{id}` / `PUT /{id}` / `DELETE /{id}` с несуществующим id.
- [ ] **Duplicate 400/409** — попытка создать запись с уже занятым уникальным полем.
- [ ] **FK validation** — при некорректном внешнем ключе → 400 (не 500).
- [ ] Для бизнес-правил, специфичных эндпоинту (например, «при resolved
      обязательна resolved_date») — отдельный тест на каждое.

---

## Что НЕ покрыто (и почему)

- **PDF-генерация (`/object/{id}/fire-protection-log/pdf`,
  `/object/bulk-fire-journal`).** Требует WeasyPrint + кучу шрифтов и
  reference-PDF для сверки. Покрытие осмысленно делать визуальными
  snapshot-тестами в отдельном CI-job — это другой класс тестов.
- **Загрузка файлов через `report_attachment` / `issue_attachment`.**
  Требует моков `MEDIA_PATH` и валидных JPEG/PDF — добавьте отдельный
  модуль `test_attachments.py` с фикстурой временной media-папки.
- **Миграции Alembic.** См. секцию «Не использую миграции».
- **Логирование/middleware** (`middleware.LogRequestsMiddleware`). Эффект
  виден только в логах — тесты по логам это другой класс, чем тесты API.
- **CRUD на каждый из 32 справочников.** Покрыт один (spec_priority) — он
  представительный. Остальные дописываются по шаблону, если в них находятся
  баги или появляются специфические бизнес-правила.

---

## Troubleshooting

### `OperationalError: database "autoreport_test" does not exist`

Создайте её — см. [Подготовка тестовой БД](#подготовка-тестовой-бд).

### `InvalidAuthorizationSpecificationError no pg_hba.conf entry for ...`

Сервер PostgreSQL не пропускает ваш хост к указанной БД. Это про
**удалённый prod-сервер**: на нём `pg_hba.conf` whitelist'ит только
`autoreport`. Используйте локальный Postgres (`DB_HOST=127.0.0.1
DB_PORT=5433`), как описано в TL;DR.

### `ModuleNotFoundError: No module named 'pytest_asyncio'`

```bash
poetry install --with dev
```

### `ModuleNotFoundError: No module named 'pytest_timeout'`

```bash
poetry run pip install pytest-timeout
```

(в `pyproject.toml` пока не вписан — добавьте в dev-deps если хочется.)

### Тест висит в teardown, упирается в `GetQueuedCompletionStatus`

Это значит, что на Windows активен `ProactorEventLoop`. Проверьте, что
`conftest.py` в самом верху ставит `WindowsSelectorEventLoopPolicy`.

### `InterfaceError: cannot perform operation: another operation is in progress`

Скорее всего ваш тест использует `db_session` в теле **после** вызова
`client.*()`. См. ограничение в секции
[conftest.py — что важно понимать](#conftestpy--что-важно-понимать).
Создавайте данные либо до `client`-вызовов, либо через API.

### `Future attached to a different loop`

Проверьте, что патч NullPool в `conftest.py` отрабатывает (он стоит до
импортов проекта). Можно ассертить из shell:

```bash
poetry run python -c "
import sys; sys.path.insert(0, 'tests')
import conftest
print(type(conftest.engine.pool).__name__)  # должно быть 'NullPool'
"
```

### `RuntimeError: Event loop is closed`

Скорее всего вы добавили async-фикстуру со scope=`function`, которая работает
с engine'ом. Engine привязан к session-loop. Решение: либо переведите
фикстуру в session-scope, либо не открывайте новые engine'ы — используйте
`db_session` фикстуру.

### `asyncpg.exceptions.UndefinedTableError`

Скорее всего вы добавили новую модель и не импортировали её в `conftest.py`
в блок `import model.<name>  # noqa: F401`. SQLAlchemy не знает про
таблицу, потому что класс модели не загрузился.

### `NotNullViolationError: ... в "users"` или другой таблице

Фабрика `create_user`/`create_*` не передаёт значение для NOT NULL поля.
Посмотрите модель (`model/<entity>.py`), какие поля без `nullable=True`,
и проставьте дефолты в фабрике.

### Тесты загрязняют боевую БД

Если в conftest'е env-override отрабатывает, такого не будет. Если
сомневаетесь — проверьте `DB_NAME` через:

```python
import config
print(config.settings.DB_NAME)
# должно быть autoreport_test (или то, что задано через TEST_DB_NAME)
```

### Хочу запустить один тест и иметь данные после прогона

```bash
poetry run pytest tests/test_issue.py::test_create_issue_success -p no:cacheprovider
```

Фикстура `_truncate_between_tests` чистит таблицы **после** теста, чтобы
последний срез данных был виден в pgAdmin/psql сразу после падения.

---

## CI

Минимальный workflow для GitHub Actions:

```yaml
# .github/workflows/tests.yml
name: tests
on: [push, pull_request]
jobs:
  pytest:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: autoreport_test
          POSTGRES_USER: autoreport
          POSTGRES_PASSWORD: autoreport
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install poetry==1.8.3
      - run: poetry install --with dev
      - run: poetry run pip install pytest-timeout
      - run: poetry run pytest --timeout=60
        env:
          DB_HOST: localhost
          DB_PORT: 5432
          DB_NAME: autoreport_test
          DB_USER: autoreport
          DB_PASSWORD: autoreport
          SECRET_KEY: ci-secret-key-for-tests
          ALGORITHM: HS256
          ACCESS_TOKEN_EXPIRE_MINUTES: 30
          REFRESH_TOKEN_EXPIRE_DAYS: 30
```

> На Linux-CI Selector loop policy и NullPool patch всё равно работают
> (просто там они не строго обязательны — Proactor-IOCP-проблемы Windows-only).
> Конфигурацию менять не нужно.
