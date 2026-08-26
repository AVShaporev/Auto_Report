# Changelog

Все значимые изменения Auto_Report (backend). Формат по
[Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование [SemVer](https://semver.org/lang/ru/) — bump на каждый
фикс/фичу; см. правило в feedback_autoreport_versioning.md.

## [1.0.19] — 2026-08-26

### Changed
- `LogRequestsMiddleware` больше не пишет `/api/health` в JSONL-лог —
  master-monitoring дёргает health каждые пару минут, шум забивал
  «Технические логи» в master-UI (`TechLogsView` из #312 Фаза 2).
  Текстовый loguru-лог `/api/health` продолжает писаться в stdout
  контейнера — контейнер-логи ротируются отдельно.

## [1.0.18] — 2026-08-27 (Фаза 2 из #312 — тенант-часть)

### Added
- `GET /api/tenant/tech-logs` — тот же JSONL что старый
  `/api/log/list`, но auth через `MASTER_API_TENANT_TOKEN` (shared
  secret между master и тенантом — тот же токен тенант шлёт в master
  для `/api/lifecycle/{slug}`, используем в обе стороны). Master
  ходит сюда с `https://<slug>.cool-doc.ru/api/tenant/tech-logs` и
  рендерит в своей master-UI `TechLogsView` (в разработке).
- `service/log.py`: рефакторинг — общая логика вынесена в
  `_list_logs_core`, новая функция `list_logs_for_master()` для
  master-inbound без RBAC-проверки.
- `_require_master_token` guard в `api/tenant.py` — проверяет
  `Authorization: Bearer <token>` против `MASTER_API_TENANT_TOKEN`.

### Notes
- Работает автоматом на любом новом SaaS-тенанте: endpoint в общем
  образе, `MASTER_API_TENANT_TOKEN` пробрасывается provision-tenant.sh.
- Старый `/api/log/list` пока живой — используется никак (LogsView
  переехал на `/api/activity_log/list` в v1.0.14), но оставляю до
  завершения Фазы 2.

## [1.0.17] — 2026-08-25

### Added
Расширил `log_activity()` на все ключевые CRUD-сущности (в дополнение
к order/report/issue/auth из v1.0.14):
- `service/object.py` — create/update/delete.
- `service/contract.py` — create/update/delete.
- `service/equipment.py` — create/update/delete.
- `service/organization.py` — create/update/delete.
- `service/objects_equipment.py` — add/update/delete.
- `api/role.py` — create/update/delete (пишется на API-уровне через
  отдельную `new_session`, т.к. role_service не принимает current_user).
- `api/user.py` — create/update/delete (тот же паттерн).

Справочники `spec_*` не покрыты сознательно (шум, справочники правятся
редко). При необходимости — добавим в next-cycle.

## [1.0.16] — 2026-08-25

### Fixed
- `activity_log` записи не сохранялись: `create_activity_log` в
  data-слое делал только `session.flush()`. По паттерну проекта
  data-функции сами коммитят (`await session.commit()` в конце). К
  моменту вызова `log_activity` из service после мутации основная
  транзакция уже была closed, наш INSERT попадал в новую auto-tx и
  откатывался при `async with new_session()` __aexit__ (`session.close()`
  без commit).
- Заменил `flush()` → `commit()` в `data/activity_log.py::create_activity_log`.

## [1.0.15] — 2026-08-25

### Fixed
- `GET /api/activity_log/list` → 500 `column activity_logs.description
  does not exist`. Родная миграция `c2f5b8a3d941` упустила Base-cols
  `description` (у нас все модели наследуют его от `Base`). SQLAlchemy
  всё равно включает эту колонку в SELECT — таблица без неё падает.
- Новая миграция `c8a4d3e2f9b7` — `ALTER TABLE activity_logs ADD
  COLUMN description VARCHAR NULL`.
- Тот же паттерн уже пойман раньше: idempotency_keys (v1.0.4-ish,
  `c5e6f7a8b9c0`) и media_upload_sessions (`d7f8a9b0c1e2`). Пора
  зафиксировать правило в auto-memory.

## [1.0.14] — 2026-08-25 (Фаза 1 из #312)

### Added — журнал пользовательских действий (activity_log)
- Alembic-миграция `c2f5b8a3d941`: таблица `activity_logs`
  (id, user_id NULL→users, user_name-снапшот, action, entity, entity_id,
  summary, details JSONB, created_at, updated_at + 3 индекса).
- Модель `model/activity_log.py`, DAO `data/activity_log.py`,
  service `service/activity_log.py` с helper'ом `log_activity(session,
  user, action, entity, entity_id, summary, details=None)`. Пишется
  в той же сессии что и основная мутация (rollback синхронный).
  Ошибки логирования не пробрасываются (loguru.warning).
- `GET /api/activity_log/list` — фильтры по user_id/entity/action/дате
  + ILIKE-поиск в summary/user_name + пагинация. Только для админов.
- Схема `schema/activity_log.py` — `ActivityLogResponse`.

### Wired-in log_activity()
Все ключевые мутации инженерского пути:
- `service/order.py` — create, update, change_status, delete.
- `service/report.py` — create, update, change_status, delete.
- `service/issue.py` — create, update, change_status, delete.
- `api/auth.py` — login, logout.

### Notes
- Фаза 2 (технические JSONL-логи в admin.cool-doc.ru) — отдельным
  релизом. Текущий `/api/log/list` остаётся живым, но пункт «Логи»
  во фронте тенанта заменён на «Действия» (activity_log).
- События до внедрения (2026-08-25) в новом журнале не появятся —
  история начинается с момента миграции.

## [1.0.13] — 2026-08-24

### Changed
- QR-код заявки больше **не** втыкается автоматически в конец каждого
  акта (v1.0.12). Теперь это docxtpl-переменная `{{ qr }}` — автор
  шаблона сам решает вставлять её и где именно; подпись рядом (если
  нужна) пишет тоже сам.
- Убран `_append_qr_to_docx`, добавлен `_make_qr_bytes` — генерит PNG
  в память, передаётся в контекст как `InlineImage(doc, buf, width=Mm(30))`.
- Старые шаблоны без `{{ qr }}` продолжают работать как раньше — акт
  просто без QR.

Документация: см. `Auto_report_front/src/docs/articles/templates-placeholders.md`,
новый раздел «`qr` — QR-код заявки для мобильного приложения».

## [1.0.12] — 2026-08-24

### Added
- В конце PDF/DOCX-акта по заявке (`render_order_document`) теперь
  вставляется QR-код с URL `https://<TENANT_SLUG>.cool-doc.ru/orders/<id>`
  + подпись «📱 Сканируйте QR-код в мобильном приложении…».
  Инженер сканирует его в mobile-приложении (v1.6.0+) и попадает
  напрямую в OrderDetailView этой заявки. Работает и для bulk-zip
  (тот же путь через `render_order_document`).
- Dependency: `qrcode[pil] ^8.0` в main deps (не dev — Dockerfile
  ставит без dev-группы, см. httpx-инцидент 2026-08-09).

Если `TENANT_SLUG` не задан — QR не добавляется, акт рендерится как раньше.

## [1.0.11] — 2026-08-24

### Added
- `MobileObjectSummaryItem` / `/api/mobile/objects` — новые поля:
  - `street_name`, `address_full` (полный: регион + район + нас.пункт +
    улица + дом + помещение; собирается в Python из компонентов чтобы
    пропускать NULL) — для карточки списка объектов в mobile.
  - `customer_short_name` (JOIN Contract → Organization.short_name) —
    для фильтра «Заказчик» в mobile ObjectsListView.
- `MobileOrderListItem` / `/api/mobile/orders` — новые поля
  `region_name`, `arial_name`, `locality_name` (JOIN Object → Region/
  Arial/Locality) — для каскадных фильтров в mobile OrdersListView.

## [1.0.10] — 2026-08-24

### Added
- `MobileObjectSummaryItem`/`GET /api/mobile/objects` теперь возвращает
  `region_name`, `arial_name`, `locality_name` — для фильтров в mobile
  `ObjectsListView` (по региону / району / нас. пункту, вместо фильтра
  по договорам). Backend-side JOIN на Region/Arial/Locality.

## [1.0.9] — 2026-08-24

### Added
- `GET /api/mobile/object-equipment/{oe_id}` → `MobileObjectEquipmentDetail`
  — compact-детали одной единицы оборудования для drill-down в mobile
  APK (`ObjectEquipmentDetailView`). Без RBAC-проверки: у роли
  инженера часто нет `object_equipment_read`, а тап на карточку должен
  открывать детали. Общий Bearer JWT достаточно (аналогично остальным
  `/api/mobile/*` endpoint'ам).
- Схема `MobileObjectEquipmentDetail`: object_equipment_id, equipment_id,
  equipment_name, equipment_type_name, system_name, count, inventory_number,
  serial_number, installation_date, object_id, object_name, open_issues_count.

## [1.0.8] — 2026-08-23

### Added
- Три bulk-endpoint'а для mobile-prefetch:
  - `POST /api/mobile/orders/bulk-details` body `{ids: [1,2,...]}` →
    `List[OrderResponse]` (полные детали заявок).
  - `POST /api/mobile/objects/bulk-details` → `List[ObjectResponse]`.
  - `POST /api/mobile/reports/bulk-details` → `List[ReportResponse]`.
- Все требуют Bearer JWT (`get_current_user`); внутри цикл по
  существующим `get_*_with_details` сервисам с check_permission,
  так что RBAC сохраняется. Один HTTPException (404/403) по конкретному
  ID тихо пропускается — sync остальных не рушится.
- Заменяют N+1 GET-запросов в `Auto_Report_Mobile/prefetch.js` (было
  50 заявок → 50 отдельных GET'ов) одним POST на сущность.

## [1.0.7] — 2026-08-23

### Fixed
- `UserUpdate.email` был `Optional[EmailStr]`, но во всех остальных
  схемах (`UserBase/Response/List`) email — просто `str`. В БД
  встречаются dev-адреса без валидного TLD (`admin@local`,
  `ivan@company`), которые Pydantic v2 `EmailStr` режет как
  «not a valid email address». Симптом: PUT `/api/user/{id}` падал
  «Ошибка валидации E-mail: value is not a valid email address:
  The part after the @-sign is not valid» при обычной смене пароля
  (фронт отправляет весь объект, старый email проходит валидацию).
  Заменил на `Optional[str]` — consistency + fix regression.

## [1.0.6] — 2026-08-19

### Changed (Ops)
- `deploy-vds.yml` после успешного hi-tech healthcheck теперь дополнительно
  запускает fan-out `redeploy-tenants.sh --skip-caddy-reload` для всех
  SaaS-тенантов (`/opt/auto-report/tenants/<slug>/`), затем `caddy reload`
  один раз. Раньше это была ручная операция после каждого merge в prod
  (`sudo redeploy-tenants.sh --pull`), теперь автомат.
- Параллельный запуск с front-fan-out'ом сериализуется через `flock -w 900
  /tmp/redeploy-tenants.lock` — иначе `docker compose up -d --force-recreate`
  из двух workflow'ов гонятся за один контейнер.

### One-time VDS setup (нужно до первого merge в prod с этими workflow):
```
# 1. Симлинк на короткий путь — иначе длинная sudoers-строка рвётся
#    в некоторых терминалах (paste-instability) и файл невалиден.
SRC=/opt/auto-report-master/Auto_Report_Master/scripts/redeploy-tenants.sh
sudo ln -sf "$SRC" /usr/local/sbin/tenants-redeploy

# 2. sudoers — редактируй через `sudo visudo -f ...` или nano,
#    ВРУЧНУЮ напечатай одну строку:
#      deploy ALL=(root) NOPASSWD: /usr/local/sbin/tenants-redeploy, /usr/local/sbin/tenants-redeploy *
sudo nano /etc/sudoers.d/deploy-redeploy-tenants
sudo chmod 440 /etc/sudoers.d/deploy-redeploy-tenants
sudo visudo -c        # должно быть три "parsed OK"

# 3. Проверка что sudo без пароля работает
sudo -n /usr/local/sbin/tenants-redeploy --help
```
Без этой настройки GHA-step SSH-ится под `deploy`, `sudo tenants-redeploy`
запрашивает пароль, ssh-action висит до command_timeout.

## [1.0.5] — 2026-08-19

### Security
- `POST /api/user/create` и `PUT /api/user/{id}` теперь запрещают
  назначать роль с `is_superadmin=True`, если вызывающий сам не
  суперадмин (было: любой юзер с `user_create` / `user_modify` мог
  выдать себе или коллеге полный superadmin). Возвращает 403 «Роль
  superadmin может назначить только суперадминистратор.». Общая
  проверка вынесена в `_assert_can_assign_role()` в `api/user.py`.
- Юзеры с `is_superadmin`-ролью на bootstrap создаются напрямую в БД
  (`bootstrap_admin.py`) — этот путь по-прежнему разрешён.

## [1.0.4] — 2026-08-18

### Added (mobile drill-down с ObjectDetailView)
- `GET /api/mobile/orders`, `/mobile/reports`, `/mobile/issues` — новый
  query-параметр `object_id` (drill-down: только по указанному объекту).
- `GET /api/mobile/object-equipment?object_id=X` — новый endpoint,
  compact-список единиц оборудования на объекте
  (`object_equipment_id`, equipment name/id/count, инв.номер,
  серийный номер, счётчик открытых неисправностей).
- `schema.mobile.MobileObjectEquipmentItem` — соответствующая схема.

Мобилка использует эти endpoint'ы чтобы дать инженеру провалиться из
карточки объекта в списки «оборудование / заявки / отчёты / неисправности».
Web-фронт не затрагивается.

## [1.0.3] — 2026-08-16

### Fixed
- RoleBase pydantic-схема не содержала 4 новых поля
  `spec_order_status_read/create/modify/delete` — фронт слал их при
  сохранении роли, Pydantic отбрасывал → PUT `/api/role/{id}` не
  обновлял эти колонки, права спокойно не сохранялись. Дополнил.

## [1.0.2] — 2026-08-16

### Changed
- `GET /api/spec_order_status/options` теперь требует право
  `spec_order_status_read` (было публичным). Юзеры без права
  получают 403 → фронт скрывает бейджи/фильтры статусов заявок.
  Create Order без status_id по-прежнему работает — бэк подставляет
  is_default для рядовых юзеров.

## [1.0.1] — 2026-08-16

### Fixed
- `PUT /api/spec_order_status/{id}` с `is_default=true` падал 500
  (partial unique constraint violation 23505). SQLAlchemy отправлял
  UPDATE'ы в непредсказуемом порядке — сначала SET true у новой строки,
  потом SET false у старой, в промежутке два default=true.
  `_unset_current_default` теперь делает явный `UPDATE ... SET
  is_default=false` через SQL + `session.flush()` — старая гарантированно
  сброшена в БД до последующего SET true.

## [1.0.0] — 2026-08-16

Первая версия с формальным версионированием. Проект давно в prod у hi-tech,
за это время проделаны все этапы: базовый CRUD, SaaS multi-tenant,
Mobile M1-M6, docker+CI/CD, канон spec_order_statuses и др.

### Added
- `VERSION` файл в корне репо.
- `main.py` логгирует `📦 Auto_Report v{ver} starting…` при старте.
