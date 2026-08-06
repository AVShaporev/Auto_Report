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

### QR-onboarding (Mobile M1.6)
- `POST /api/auth/mobile-onboard` — body `{token}`. Валидирует HS256-JWT общим ключом `MOBILE_ONBOARD_SECRET` (shared с master). Проверяет `type=mobile_onboard`, `tenant=TENANT_SLUG`, sub-user существует и активен. Выпускает обычную пару (access, refresh) через существующий `issue_session_pair` (M1.1) — с session-row в user_sessions.
- Токен генерирует master: `POST /api/tenants/{slug}/mobile-onboard-token` (см. Auto_Report_Master). Клиент сканирует QR → парсит URL → передаёт token сюда → получает `{user, access_token, refresh_token}`.
- Если `MOBILE_ONBOARD_SECRET` не задан → 503 (feature disabled).
- Если токен на другой tenant → 401 «Token issued for different tenant».

### Chunked media upload (Mobile M1.5)
- `POST /api/mobile/media/upload/init` — `{kind, filename, total_size}` → `{upload_id, max_chunk_size, expires_at}`. Создаёт tmp-файл в `MEDIA/mobile/tmp/`.
- `PUT /api/mobile/media/upload/{upload_id}` с `Content-Range: bytes X-Y/TOTAL` и бинарём body → append chunk. Валидирует что chunk идёт по порядку.
- Финальный chunk (received==total) автоматически финализируется: Pillow resize (max 2000px, JPEG q=80) → move в `MEDIA/mobile/<uuid>_<name>.jpg` → возврат `final_path`.
- `GET /api/mobile/media/upload/{upload_id}` — статус.
- Лимиты: MAX_UPLOAD_SIZE=50 MB, MAX_CHUNK_SIZE=5 MB, session TTL=1 час. Cleanup expired session'ов + orphan tmp-файлов @03:45 МСК.

### Idempotency-middleware (Mobile M1.4)
- Заголовок `X-Idempotency-Key: <uuid>` (8-128 printable-ASCII) на POST/PUT/PATCH/DELETE.
- Middleware декодит Bearer-JWT → user_name, scope'ит ключ по (user, key).
- При повторном запросе с тем же ключом (<24 ч) возвращает закэшированный ответ + `X-Idempotent-Replay: true`.
- Кэшируется **только 2xx**, TTL 24 ч, cleanup daily @03:30 МСК.
- Без header'а или без auth — middleware прозрачно пропускает.

### Push-tokens (Mobile M1.2)
- `POST /api/user/me/push-token` — upsert `{platform, token, device_id?, app_version?}`. platform ∈ {ios, android, web}. Один и тот же `token` может «переехать» с юзера A на юзера B при смене логина на устройстве.
- `DELETE /api/user/me/push-token` — body `{token}`, снимает регистрацию (только своего юзера).
- `GET /api/user/me/push-tokens` — свой список для UI/дебага.
- Cleanup: APScheduler ежедневно в 03:15 МСК сносит записи с `last_seen_at < NOW-30d`.
- **Отправка** уведомлений (FCM/APNs) ещё НЕ реализована — это Mobile M7. Пока только инфра.
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
Фронт по умолчанию ходит через Vite-proxy на `localhost:8000` (same origin, CORS не задействован).
В prod фронт живёт за общим Caddy-хостом с бэком — тоже same origin.

**CORS** подключён в `main.py` для mobile-Capacitor-app'а и dev-стендов:
- Regex покрывает `capacitor://localhost`, `https://localhost(:port)?`, `https://<любой>.cool-doc.ru`.
- Доп-origins через env `EXTRA_CORS_ORIGINS` (запятыми), например `https://192.168.1.3:5174` для smoke-теста mobile-dev'а с ноута.
- `allow_credentials=False`, `allow_methods=["*"]`, `allow_headers=["*"]`, `expose_headers` включают `Content-Disposition` (mobile читает имя файла) и `X-Idempotent-Replay`.
