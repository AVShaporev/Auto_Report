# Auto_Report — FastAPI backend

Асинхронный REST-API для управления отчётностью ТО: контракты, объекты, оборудование, заявки, неисправности, отчёты, пользователи/роли. Парный фронт — `..\Auto_report_front\auto_report_front` (Vue 3 SPA).

## Стек
- Python 3.11, FastAPI 0.115, uvicorn
- SQLAlchemy 2.0 (async) + asyncpg, PostgreSQL
- Alembic для миграций
- Pydantic v2 (+ pydantic-settings)
- python-jose (JWT HS256), passlib/bcrypt
- Loguru для логирования
- Poetry для управления зависимостями

## Запуск
```bash
# из корня Auto_Report
poetry install                          # один раз
poetry run python main.py               # localhost:8000, reload включён
# либо
poetry run uvicorn main:app --reload --host localhost --port 8000
```

Swagger UI — `http://localhost:8000/docs`, ReDoc — `/redoc`.

## Миграции
```bash
poetry run alembic upgrade head                       # применить все
poetry run alembic revision --autogenerate -m "msg"   # новая миграция
poetry run alembic downgrade -1                       # откатить одну
```

## Слои
```
main.py              точка входа, подключает все роутеры, настраивает Loguru
middleware.py        LogRequestsMiddleware — логирование запросов
config.py            Pydantic Settings из .env, get_db_url(), get_auth_data()
database/database.py async engine, async_session_maker, Base (DeclarativeBase), аннотации столбцов
api/                 роутеры FastAPI (префикс /api/<entity>), принимают depends, вызывают service/
service/             бизнес-логика, работа через DAO / new_session
data/                DAO-запросы к БД (часто через сессию, переданную снаружи)
model/               SQLAlchemy-модели, model/dao.py — UsersDAO с find_with_role
schema/              Pydantic-схемы запросов/ответов, pagination.py (PaginationParams, PaginatedResponse[T])
migration/           Alembic: env.py, versions/
core/dependencies.py get_current_active_user, require_role_read/create/modify/delete, require_any_role_permission
errors.py            доменные исключения: Missing, Duplicate, BaseLocking
utils/               timer и т.п.
templates/           jinja-шаблоны (если есть)
```

## Соглашения
- Все роутеры подключаются в `main.py` и имеют префикс `/api/<entity>`.
- На каждую сущность стандартный CRUD: `GET /list` (пагинация+фильтры), `GET /all`, `GET /options`, `GET /{id}`, `POST /create`, `PUT /{id}`, `DELETE /{id}`.
- Пагинация — через `PaginationParams` depends (`page`, `per_page` → `skip`, `limit`). Ответ — `PaginatedResponse[T]` (`items`, `total`, `page`, `per_page`, `pages`).
- Имя пользователя — поле `name` (НЕ `username`), оно же кладётся в JWT как `sub`.
- RBAC: плоские флаги на модели `Role` — `<entity>_read/create/modify/delete` плюс `is_admin`, `is_superadmin`. Проверяется либо явно внутри хендлера (`if not current_user.role.xxx`), либо через фабрики депендов в `core/dependencies.py`.
- Таблицы именуются по классу в lowercase + `s` (см. `Base.__tablename__`).

## Auth
- `POST /api/auth/login` — OAuth2 form `{ username, password }` → `{ user, access_token, refresh_token }`. Создаёт запись `user_sessions` (jti = refresh.jti).
- `POST /api/auth/refresh` — JSON body `{ refresh_token }`. Если jti есть в `user_sessions` — rotate: старая помечается `revoked_at`, выдаётся новая пара. Если записи нет (легаси-токен до Mobile M1.1) — fallback: только новый access, refresh не ротируется. Отозванный/просроченный jti → 401.
- `POST /api/auth/logout` — `{ refresh_token }` + Bearer access. Помечает свою сессию revoked.
- `GET /api/auth/sessions` — список активных сессий текущего юзера.
- `POST /api/auth/sessions/{id}/revoke` — отозвать конкретную сессию.
- `POST /api/user/{id}/revoke-all-sessions` — админ: разлогинить юзера везде.
- `GET /api/auth/me` — требует Bearer-токен, возвращает текущего юзера.
- Access 30 мин, refresh 30 дней, алгоритм HS256, секрет в `.env`.

## `.env`
```
DB_HOST=...
DB_PORT=5432
DB_NAME=autoreport
DB_USER=autoreport
DB_PASSWORD=...
SECRET_KEY=...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
```
`.env` в `.gitignore` и в git-истории отсутствует. `SECRET_KEY` ротирован 2026-04-18 (сгенерирован через `secrets.token_urlsafe(64)`). Пароль БД (`DB_PASSWORD`) пока не ротирован — вынесено в отдельный пункт.

## Известные баги (TODO)
_Все пункты закрыты. Оставь этот раздел для будущих находок._

## Связь с фронтом
Фронт по умолчанию ходит через Vite-proxy на `localhost:8000`. CORS middleware не подключён — в проде поставить reverse-proxy (nginx) либо добавить `CORSMiddleware`.
