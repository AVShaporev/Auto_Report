# Changelog

Все значимые изменения Auto_Report (backend). Формат по
[Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование [SemVer](https://semver.org/lang/ru/) — bump на каждый
фикс/фичу; см. правило в feedback_autoreport_versioning.md.

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
