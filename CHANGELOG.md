# Changelog

Все значимые изменения Auto_Report (backend). Формат по
[Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование [SemVer](https://semver.org/lang/ru/) — bump на каждый
фикс/фичу; см. правило в feedback_autoreport_versioning.md.

## [1.0.69] — 2026-09-19

### Added — подпись заказчика под отчётом
- Миграция `e7f8a9b0c1d2`: `reports.signature_path`, `signer_name`,
  `signer_position`, `signed_at`.
- `customer_signature` ({image: data URL PNG, signer_name, signer_position?,
  signed_at?}) в `ReportCreate` и `ReportUpdate`: подпись едет вместе с отчётом,
  в т. ч. через офлайн-очередь мобилки. В update: объект — заменить, `null` —
  убрать, не передано — не трогать. После утверждения отчёта — 400.
- `service/report_signature.py`: проверка (PNG, ≤ 400 КБ, не пустая),
  прозрачный фон → белый, обрезка полей вокруг росчерка, ширина ≤ 1600;
  файл в MEDIA/reports/<id>/, старый удаляется.
- `GET /api/report/{id}/signature` — PNG (право report_read).
- `ReportResponse` (и `/mobile/reports/bulk-details`): `has_signature`,
  `signer_name`, `signer_position`, `signed_at`.
- Акт: `{{ customer_signature }}` — картинка 4 см (пусто, если подписи нет),
  `{{ report.signer_name }}`, `{{ report.signer_position }}`,
  `{{ report.signed_at }}` (ДД.ММ.ГГГГ ЧЧ:ММ МСК), `report.is_signed`.
- Fix: локальный `from docx.shared import Mm` в render_order_document
  затенял модульный импорт.
- `tests/test_report_signature.py` — 4 теста, включая картинку в готовом .docx.

## [1.0.68] — 2026-09-19

### Added — импорт объектов и оборудования из Excel
- `GET /api/import/objects/template` — шаблон .xlsx: листы «Объекты»,
  «Оборудование», «Справочники»; выпадающие списки из справочников
  организации (регион, тип строения/помещения, периодичность — строгие;
  район, НП, система, оборудование — подсказки), подсказки в примечаниях.
- `POST /api/import/objects/preview` (multipart: `contract_id`, `file`) —
  разбор без записи: что создастся, какие справочники добавятся, ошибки по
  строкам (обязательные поля, длины, нет в справочнике, дубль объекта или
  позиции, нет объекта для оборудования, кол-во, дата, лимит тарифа).
- `POST /api/import/objects/commit` — при ошибках 400 с предпросмотром и без
  записи; иначе создаёт недостающие справочники (район, НП и улица с типом из
  сокращения «г.»/«ул.», система, тип оборудования, оборудование), объекты —
  через `create_object` (лимит тарифа, автогенерация заявок, журнал),
  оборудование — через `add_equipment_to_object`. Повторная загрузка того же
  файла ничего не дублирует: объекты «уже есть», позиции «пропущено».
- Права — как у ручного ввода: `object_create` + `object_equipment_create`.
- Зависимость `openpyxl` (pyproject + poetry.lock).
- `tests/test_import_objects.py` — 4 теста.

## [1.0.67] — 2026-09-19

### Added — новые метки docxtpl-шаблонов: отчёт, работы, неисправности, история
- Акт заявки (`_build_context`):
  - `order.type`, `order.status`, `order.created_at_long`, `order.due_date`,
    `order.period_start`, `order.period_month` («сентябрь 2026» — период
    плановой заявки, иначе месяц создания), `order.assigned_to`;
  - `report.*` — отчёт по заявке: `number`, `date`, `date_long`, `month`,
    `description`, `engineer`, `status`, `is_approved` (пустые строки, если
    отчёта нет);
  - `works` / `works_groups` — регламентные работы из справочника «Операции»
    по типам оборудования объекта (без дублей, с периодичностью);
  - `issues_open` — неустранённые неисправности объекта (замечания в акте),
    `issues_fixed` — неисправности, устранённые этой заявкой.
- Журнал объекта (`_build_journal_context`): `equipment_groups`, `works`,
  `works_groups`, `reports` (утверждённые отчёты по дате: дата, что сделано,
  инженер, вид и номер заявки), `issues` (все неисправности объекта),
  `issues_open`.
- Загрузка связей — `_object_equipment_loads()` (оборудование → тип →
  операции → период, система, неисправности со статусом/приоритетом) для
  заявки и журнала; отчёт заявки с автором и статусом; отчёты объекта с
  заявкой и её типом.
- Старые шаблоны не затронуты: ключи только добавлены.
- `tests/test_render_context.py` — 4 теста: словари акта и журнала, акт без
  отчёта, рендер таблицы `{%tr for r in reports %}` в .docx.

## [1.0.66] — 2026-09-19

### Added — авто-«Устранена» при утверждении отчёта по заявке на устранение
- `PATCH /api/report/{id}/status` → «Утверждён»: неисправности, у которых
  заявка на устранение (`issues.order_id`) закрыта этим отчётом
  (`orders.report_id`), и которые ещё не устранены, получают статус с кодом
  `resolved`, `is_resolved`, `resolved_date` = сегодня + запись в журнале.
  Нет системного статуса `resolved` — ничего не трогаем. Обратного хода нет
  (отмена утверждения неисправность не «разустраняет»).
- `tests/test_fix_order.py`: сквозной сценарий (заявка на устранение с типом
  `fix` по умолчанию, номер `…/РЕМ/1`, связь в обе стороны, 400 на вторую
  заявку, утверждение отчёта → «Устранена») + отчёт без заявок на устранение
  ничего не меняет.

## [1.0.65] — 2026-09-19

### Fixed — дубли типа в адресе объекта/организации
- На демо адрес выглядел «г. Москва Город, ЦАО Административный округ,
  г. Москва, ул. ул. Тверская»: названия введены вместе с типом, а
  `build_address` дописывал тип ещё раз; Москва — и регион, и город.
- Новый `service/address.py` (общий для `build_address` и
  `_build_org_address`): тип не добавляется, если название уже с ним
  («ул. Тверская», «Тверская улица») или начинается со своего сокращения
  («г. Москва» при типе «Город»); одинаковые части не повторяются; номер
  дома/помещения с уже указанным «д.»/«оф.» не дублируется. Обычные адреса
  не меняются («Московская область, Одинцовский район, г. Одинцово, ул. Ленина, …»).
- Демо: «г. Москва, ЦАО Административный округ, ул. Тверская, д. 5».
  Адрес — в актах, журналах, карточках, ссылках на карты.
- `tests/test_address.py` — 7 тестов (без БД).

### Note
- `tests/test_autogen_orders.py`: 12 тестов падают и на 1.0.60 (до изменений
  2026-09-19) — фикстуры не засевают статус заявки по умолчанию
  (`get_default_status_id` → NoResultFound). Техдолг, не регрессия.

## [1.0.64] — 2026-09-19

### Added — `GET /api/mobile/order-types`
- Все типы заявок (`id`, `name`, `short_name`, `code`) для фильтра «по типу»
  в списке заявок мобилки (mobile ≥ 1.7.19). Только авторизация, как у
  `/mobile/orders`: у роли инженера может не быть `spec_order_read`.

## [1.0.63] — 2026-09-19

### Fixed — форма заявки на устранение не выбирала тип «Устранение неисправности»
- `GET /api/spec_order/all` и `/options` собирали ответ вручную и не отдавали
  `code` (в схемах поле было). Фронт ищет тип по `code === 'fix'` → не находил,
  поле «Тип заявки» оставалось пустым. Теперь `code` в обоих ответах.
  Найдено после выката 1.0.62 на demo.

## [1.0.62] — 2026-09-18

### Added — системный тип заявки «Устранение неисправности»
- Миграция `d6e7f8a9b0c1`: в `spec_orders` сидится системный тип
  «Устранение неисправности» (short_name «РЕМ», code `fix`, sla_kind `manual` —
  срок ставит менеджер). Номер такой заявки — `…/РЕМ/N`, а не `…/АВАР/N`.
- `OrderCreate.spec_order_id` теперь необязателен, но только вместе с
  `issue_id`: без типа заявка на устранение получает тип `fix`. Без `issue_id`
  и без типа — 400.

## [1.0.61] — 2026-09-18

### Added — заявка на устранение неисправности
Менеджер создаёт заявку из карточки неисправности, когда появился ЗИП, и
назначает ответственного.
- Миграция `c5d6e7f8a9b0`: `issues.order_id` (nullable FK → `orders.id`,
  `ON DELETE SET NULL`, индекс). Одна неисправность → одна заявка на устранение.
- `POST /api/order/create` принимает `issue_id`. Проверки: неисправность
  существует, на том же объекте, не устранена, заявки на устранение у неё ещё
  нет (иначе 400 с номером существующей). После создания заявки
  `issues.order_id` проставляется, статус «Новая» → «В работе», запись в журнале.
- `GET /api/issue/{id}`: новые поля `contract_id` (префилл формы заявки),
  `order_id`, `order_number`.
- `GET /api/order/{id}`: новое поле `fix_issues` — неисправности, которые
  устраняет заявка.

## [1.0.60] — 2026-09-15

### Changed — деплой hi-tech `all` больше не рестартует БД
- `scripts/deploy_vds.sh all`: `docker compose up -d --force-recreate backend
  frontend` вместо всех сервисов — postgres не пересоздаётся, как у SaaS-tenant'ов
  (Master 1.0.25 `redeploy-tenants.sh`) и master (`deploy-master.sh`). Цели
  `backend` / `frontend` не менялись.
- На VDS после merge обновить копию: `sudo cp
  /opt/auto-report/Auto_Report/scripts/deploy_vds.sh
  /opt/auto-report/scripts/deploy.sh` и сверить sha256.

## [1.0.59] — 2026-09-15

### Fixed — инженер без report_modify не мог работать со своим отчётом
Жалоба hi-tech: мобилка при сохранении отчёта с фото — «Недостаточно прав для
линковки mobile-фото». Все действия со своим отчётом после создания требовали
`report_modify`, а у роли инженера есть только `report_create`.

- Вложения отчёта (`link-mobile-photos`, загрузка, удаление) и `PUT /report/{id}`:
  достаточно `report_modify` **или** `report_create`. Проверки «только свой
  отчёт (или админ)» и «утверждённый не менять» остались.
- `PATCH /report/{id}/status`: без `report_modify` можно только отправить
  **свой** отчёт из «В работе»/«Отклонён» в «На утверждении». Утверждать и
  отклонять — по-прежнему только с `report_modify`.

### Security
- Раньше выдать инженеру `report_modify` ради фото значило дать ему менять
  статус любого отчёта (в т.ч. «Утверждён»): у смены статуса нет проверки
  автора. Теперь для фото это право не нужно. Сама смена статуса
  пользователями с `report_modify` не менялась.

## [1.0.58] — 2026-09-14

### Fixed — лимиты генерируемых полей (аудит)
Номера заявки/неисправности/отчёта собираются сервером из
`number_in_contract/MM/YYYY/customer.short_name/contract.short_subject/spec_order.short_name/N`.
При лимитах схем на исходники (short_name ≤ 100, short_subject ≤ 200,
spec_order.short_name ≤ 50) номер доходит до ~375 символов.

- Миграция `b4d5e6f7a8c9`: `orders.number` и `issues.number` VARCHAR(200) → VARCHAR(500).
  С 200 длинное сокращение предмета договора давало 500 на INSERT заявки /
  неисправности (в т.ч. в автогенерации плановых заявок).
- Модели и схемы `number` заявки, неисправности, отчёта — `max_length` 500
  (`reports.number` в БД без ограничения).
- `POST /api/issue/{id}/attachments` и `POST /api/report/{id}/attachments`:
  `title` ограничен 255 символами (колонка VARCHAR(255)) — длинный заголовок
  теперь 422, а не 500 на INSERT.

Проверено и в порядке: `reports.number` (без лимита в БД), `activity_log.summary`
(обрезается до 500 в `log_activity`), `pdf_path` вложений (≤ ~80 из 512),
`kind` (enum ≤ 20), имя файла mobile-upload (ASCII ≤ 200 + uuid < 255 байт),
refresh `jti` (uuid).

## [1.0.57] — 2026-09-14

### Fixed — 500 на создании/чтении неисправности с длинным номером
- `schema/issue.py`: `IssueBase.number` / `IssueUpdate.number` — `max_length`
  50 → 200. Колонку `issues.number` расширили до VARCHAR(200) ещё в 1.0.46,
  а схема осталась на 50: неисправность с номером длиннее 50 символов
  (`2/09/2026/Технопром/Плановое ТО котельного оборудования/Н/1`) сохранялась
  в БД, но ответ `POST /issue/create` и `GET /issue/{id}` падал
  `ResponseValidationError` → 500 без CORS-заголовков → мобильное приложение
  показывало «Нет связи с сервером», фото к неисправности не прикреплялись.
- `schema/report.py`: `ReportBase.number` / `ReportUpdate.number` — тоже
  50 → 200 (колонка `reports.number` без ограничения длины, номера того же
  формата).

## [1.0.56] — 2026-09-14

### Added — фото неисправности из мобильного приложения
- `POST /api/issue/{id}/attachments/link-mobile-photos` — `{final_paths, title?, kind='photo'}`:
  фото из chunked-upload (M1.5) склеиваются в одно PDF-вложение неисправности
  (зеркало отчётного endpoint'а, M5.3). До 10 фото за запрос.
- Права: `issue_modify` или `issue_create`; прикреплять можно только к своей
  неисправности (или админу) — инженер добавляет фото сразу после создания,
  `issue_modify` у инженерской роли обычно нет.

### Changed
- Проверка `final_path` (path-traversal, наличие файла в MEDIA) вынесена в
  `service/attachment_converter.resolve_mobile_media_paths` — общая для отчётов
  и неисправностей.
- `service/issue_attachment`: запись PDF + строки в БД вынесена в
  `_store_attachment`, её используют обычная загрузка и линковка mobile-фото.

## [1.0.55] — 2026-09-14

### Added — `customer_id` в детальных ответах заявки, неисправности, отчёта
- Рядом с `customer_name` — `customer_id` (организация-заказчик из договора),
  чтобы фронт мог сослаться на карточку организации.

## [1.0.54] — 2026-09-14

### Added — заказчик и полный адрес объекта в детальных ответах
- `GET /api/order/{id}`, `GET /api/issue/{id}`, `GET /api/report/{id}` (и
  ответы create/update, которые идут через те же функции) отдают
  `customer_name` (заказчик из договора) и `object_address` — полный адрес
  объекта через `build_address`, как в актах и `address_pretty` объекта.
- В data-слое детальных запросов явно подгружаются `locality.spec_locality`
  и `street.spec_street` (по умолчанию lazy="select" → MissingGreenlet).
- Списки не менялись: у отчётов поля добавлены только в `ReportResponse`.

## [1.0.53] — 2026-09-13

### Fixed — деплой hi-tech применял старый .env.sops
- `scripts/deploy_vds.sh` расшифровывал `deploy/secrets/vds-prod.env.sops`
  ДО `git reset --hard origin/prod`. Если правка секретов приезжала в том же
  деплое, контейнер поднимался со старым env (FCM_SERVICE_ACCOUNT_JSON на
  hi-tech подхватился только вторым деплоем). Теперь после `git reset` env
  расшифровывается повторно; ранняя расшифровка осталась как проверка ключа.
- На VDS после merge обновить копию: `sudo cp
  /opt/auto-report/Auto_Report/scripts/deploy_vds.sh
  /opt/auto-report/scripts/deploy.sh`. Копия на VDS от 2026-08-08 по размеру
  (9679 байт) совпадает с версией до `--force-recreate` (01583a3) —
  обновление подтянет и его.

## [1.0.52] — 2026-09-13

### Added — push-уведомления на hi-tech (legacy)
- `deploy/secrets/vds-prod.env.sops`: добавлен `FCM_SERVICE_ACCOUNT_JSON`
  (service account Firebase `autoreport-prod`, одной строкой) — тот же, что
  у SaaS-tenant'ов. Остальные ключи не менялись (сверено после записи).
  Применяется деплоем `deploy-vds.yml` (`--force-recreate backend`).

## [1.0.51] — 2026-09-13

### Docs — FCM-ключ общий для SaaS-tenant'ов
- `docs/PUSH_NOTIFICATIONS.md` § 1.5 и § 7, `CLAUDE.md`: ключ
  `FCM_SERVICE_ACCOUNT_JSON` хранится в master `.env.sops`, новые tenant'ы
  получают его при провижининге, существующие — через
  `Auto_Report_Master/scripts/sync-tenant-secret.sh` (Master 1.0.24).
  Устаревшее описание с монтированием файла через Docker-secret убрано.
  Кода не касается.

## [1.0.50] — 2026-09-13

### Added — фильтр по ответственному для неисправностей и отчётов

- `GET /api/issue/list?assigned_to_id=` теперь принимает `0` —
  «без ответственного» (`assigned_to_id IS NULL`), как уже было у заявок.
- `GET /api/report/list?assigned_to_id=` — новый параметр. Своего
  ответственного у отчёта нет, поэтому фильтр идёт по ответственному
  заявки, которую отчёт закрывает (JOIN `orders.report_id = reports.id`).
  `0` — отчёты по заявкам без ответственного.

## [1.0.49] — 2026-09-13

### Fixed — push при смене ответственного на существующей заявке пропускался

После v1.0.45 (создание push M7) push приходил **только** на новых заявках, а
при смене ответственного на существующей PUT /api/order/{id} возвращал 200 без
`[push]` строки в логах.

Причина: `service/order.py::update_order` считывал старое значение как
`existing.assigned_to_id` **после** вызова `order_data.update_order`, а тот
внутри мутирует ORM-instance того же самого объекта (SQLAlchemy identity map:
`get_order_by_id` в data-слое возвращает уже загруженный `existing` из
session) + `session.refresh(order)`. К моменту hook'а `existing` уже был с
новым `assigned_to_id`, и условие `new_assignee != existing.assigned_to_id`
всегда было False.

Фикс: снапшот `old_assignee_id = existing.assigned_to_id` **до** апдейта,
сравнение push-hook переведено на локальную переменную.

## [1.0.48] — 2026-09-13

### Fixed — activity_log падал на `date` в details → PUT /order 500

Юзер на demo менял ответственного заявки — вернулось 500. В стек-трейсе:

```
sqlalchemy.exc.PendingRollbackError: This Session's transaction has
been rolled back due to a previous exception during flush.
Original exception was: (builtins.TypeError) Object of type date is
not JSON serializable
[SQL: INSERT INTO activity_logs ... $7::JSONB ...]
```

Существующий баг с версии первого activity-log'а. `asyncpg` не умеет
кодировать `date`/`datetime`/`Decimal` в JSONB. Не проявлялся раньше,
потому что `update_order` обычно приходил без `due_date` в details.
С мобилки при назначении ответственного PUT приносил весь payload
включая `due_date` — 500.

- `data/activity_log.py::_jsonify_safe` — новый helper, рекурсивно
  превращает `date`/`datetime` в `isoformat()`, `Decimal` в `str`.
  Применяется к `details` перед INSERT.
- `service/order.py::update_order` push-hook — читает `new_assignee`
  из `update_data`, не через `order.assigned_to_id` (тот ORM-attribute
  expire'нут после commit, lazy-load бы валился на уже rolled-back
  session'е).

VERSION 1.0.47 → 1.0.48.

## [1.0.47] — 2026-09-13

### Changed — FCM service-account можно передавать как JSON-строку в env

Раньше `service/push.py::init_fcm()` требовал только `FCM_SERVICE_ACCOUNT_PATH`
(путь к файлу на диске → нужен volume-mount / Docker-secret). Добавлен
альтернативный способ: `FCM_SERVICE_ACCOUNT_JSON` — весь JSON целиком одной
строкой в env-переменной. Приоритет у `_JSON`, `_PATH` — fallback.

**Why:** JSON-в-env удобнее для SOPS-encrypted `.env` каждого tenant'а
(рядом с существующим MOBILE_ONBOARD_SECRET). Никаких дополнительных
volume-mount'ов в docker-compose не требуется.

- `config.py::Settings.FCM_SERVICE_ACCOUNT_JSON` — новый Optional.
- `service/push.py::init_fcm` — сначала пробует `_JSON` (парсит через
  `json.loads` + `credentials.Certificate(sa_dict)`), затем `_PATH`.
- Оба не заданы → no-op, как раньше.

VERSION 1.0.46 → 1.0.47.

## [1.0.46] — 2026-09-13

### Fixed — `issues.number` расширен `VARCHAR(50)` → `VARCHAR(200)`

Юзер поймал на демо-стенде через мобилку: `POST /api/issue/create`
падает с `500 Internal Server Error`, в логах —
`asyncpg.exceptions.StringDataRightTruncationError: value too long for
type character varying(50)`.

Причина: `service/issue.py::create_issue` генерирует номер по шаблону
`{number_in_contract}/{MM}/{YYYY}/{short_customer}/{short_subject}/Н/{seq}`.
При длинных `short_name` заказчика и `short_subject` договора итог
легко переваливает за 50 символов. Для `orders.number` та же формула
уже давно расширена до `VARCHAR(200)` — а для `issues.number`
осталось `VARCHAR(50)`, забыли.

- `model/issue.py::Issue.number` — `String(50)` → `String(200)`,
  комментарий с ссылкой на инцидент.
- `migration/versions/a3c4d5e6f7b8_issues_number_200.py` — новая
  Alembic-миграция, `ALTER TABLE issues ALTER COLUMN number TYPE
  VARCHAR(200)`. Downgrade — с предупреждением про потенциальную
  обрезку.

**Применение на живых tenant'ах:** deploy-vds.yml сам катит миграции
через существующий fan-out (`redeploy-tenants.sh`, см. memory
[feedback-autoreport-ci-tenant-fanout]) — все SaaS-tenant'ы получат
`alembic upgrade head` автоматом. Hi-tech (legacy) — отдельная
цепочка.

VERSION 1.0.45 → 1.0.46.

## [1.0.45] — 2026-09-13

### Added — Mobile M7: push-уведомления при назначении ответственного

Инфра (M1.2, v1.0.14): `push_tokens` — регистрация FCM/APNs-токенов
с телефона. **Отправка** (M7) до этого не была реализована — CLAUDE.md
это прямо констатировал. Теперь реализована.

**Полный дизайн:** [`docs/PUSH_NOTIFICATIONS.md`](docs/PUSH_NOTIFICATIONS.md).
Читать этот файл при любой правке push-логики.

Что добавилось:
- `service/push.py` — новый. Клиент Firebase Admin SDK, `send_assignment_notification`
  (мульти-каст на активные токены юзера через `messaging.send_each_for_multicast`).
- `service/order.py` — хуки:
  - `create_order` — если сразу с `assigned_to_id ≠ current_user.id` → push.
  - `update_order` — если `assigned_to_id` изменился на нового (≠ current_user) → push.
  - `bulk_assign_responsible` — по каждой затронутой заявке → push (если
    target ≠ current_user).
  Все хуки в try/except: любой FCM-фейл — только warning в лог, HTTP
  handler не ломается.
- `main.py` — `init_fcm()` в lifespan-е при старте.
- `config.py` — новые Settings `FCM_SERVICE_ACCOUNT_PATH` +
  `FCM_PROJECT_ID` (оба Optional).
- `pyproject.toml` — `firebase-admin ^6.5`.

**Feature-flag:** если `FCM_SERVICE_ACCOUNT_PATH` не задан или файл
отсутствует — `service/push.py` работает в **no-op режиме**: логгирует
warning и все `send_*`-функции возвращают 0. Приложение не падает,
все HTTP endpoint'ы работают как раньше. Активация push'ей — по
настройке Firebase (см. `docs/PUSH_NOTIFICATIONS.md § 1`).

**Deadstone-токены:** FCM-ошибки `UNREGISTERED` / `INVALID_ARGUMENT` /
`SENDER_ID_MISMATCH` помечают токен `is_active=false`. Через 30 дней
существующий APScheduler-cleanup (@03:15 МСК) их снесёт физически.

**Что НЕ покрыто в этом релизе** (задел на будущее):
- iOS/APNs — пока mobile-APK только Android, откладываем до iOS-релиза.
- Триггеры на изменение статуса заявки / готовность отчёта —
  отдельные user-facing события, отложены до M8.
- Триггеры на `Issue.assigned_to_id` — аналогично, отдельная итерация.

**Как активировать** (см. `docs/PUSH_NOTIFICATIONS.md § 1`):
1. Firebase Console → создать проект.
2. Скачать `fcm-service-account.json`.
3. Положить в SOPS-env: `FCM_SERVICE_ACCOUNT_PATH=/app/secrets/fcm-service-account.json`,
   монтировать файл в контейнер как Docker-secret.
4. Redeploy — в логах `[push] enabled: firebase-admin loaded from ...`.

VERSION 1.0.44 → 1.0.45.

## [1.0.44] — 2026-09-08

### Added — авто-переход заявки в «В работе» при создании отчёта
Когда инженер (или веб-юзер) создаёт отчёт по заявке, заявка
автоматически переходит из «Новая» в «В работе». Логика в
`service/report.py::create_report` после `log_activity`:

- Получаем `Spec_Order_Status` с `name='В работе'`.
- Если текущий статус заявки `is_default` (=«Новая»), меняем
  `order.status_id` на найденный + запись `log_activity` типа
  `update/order`. Из «Выполнена»/«Отменена» назад НЕ откатываем —
  это админ-решение.
- Изменение попадает в тот же коммит через commit из `log_activity`
  (шареная session).

Симметрично тому что отчёт создаётся сразу с default статусом
«В работе» (миграция `f3a4b5c6d7e8`) — цикл семантически
согласован: инженер начал работу → и заявка, и отчёт в
«В работе».

VERSION 1.0.43 → 1.0.44.

## [1.0.43] — 2026-09-07

### Added — Jinja-шаблоны журналов
На demo-тенанте кнопка «Скачать журнал» на объекте отдавала
400 «не загружен шаблон документа», потому что `Spec_Journal.
template_storage_path` был пустым. Добавил 2 полноценных
docxtpl-шаблона журналов.

- **journal_maint.docx** — Журнал технического обслуживания.
  Паспорт объекта + сведения о договоре + пустая таблица на 10
  строк (№ / Дата / Работы / Исполнитель / Подпись) для ручной
  регистрации записей ТО.
- **journal_primary.docx** — Журнал первичного осмотра и приёмки.
  Паспорт объекта + стороны договора + таблица на 8 строк
  (№ / Система / Состояние / Замечания) + подписи директоров.

Оба заведены с `Spec_Journal.template_storage_path = templates/
journal_*.docx` в `seed_demo.py`. Копирование в MEDIA volume —
через существующий `copy_seed_templates()`.

### Note — Journal-контекст
Контекст `_build_journal_context()` в `service/render_docx.py`
включает только `object`, `contract`, `customer`, `executor`,
`today`, `today_long`. **Нет** `order.*` и `equipment_groups`.
Поэтому в шаблонах журналов нельзя показать список оборудования
объекта — вместо этого пустые таблицы для ручных записей.
(Дальнейший шаг — расширить контекст журнала добавив
`equipment_groups` из `_build_equipment_groups(obj)` — тогда
Журнал ТО тоже сможет показать перечень.)

### Changed
- `scripts/generate_demo_templates.py`: добавлены
  `gen_journal_maint()` + `gen_journal_primary()` + утилиты
  `_add_journal_log_table()` / `_add_journal_inspection_table()`.
- `scripts/seed_demo.py`: `spec_journal_defs` теперь несёт
  `template_filename` + `template_storage_path`, идемпотентный
  поиск по `code`.

VERSION 1.0.42 → 1.0.43.

## [1.0.42] — 2026-09-07

### Changed — реальные Jinja-шаблоны в `templates/seeds/`
Прежние `emergency.docx / maintenance.docx / planned.dotx /
primary.dotx` были плейсхолдерами. Заменены на полноценные акты с
docxtpl-разметкой, чтобы на demo-тенанте кнопка «Скачать акт»
сразу показывала подстановку данных из БД.

Что теперь подставляется в каждом акте:
- `{{ order.number }}`, `{{ order.created_at }}`, `{{ order.description }}`
- `{{ contract.number }}`, `{{ contract.date_of_consclusion }}`,
  `{{ contract.date_of_completion }}`, `{{ contract.subject }}`
- `{{ customer.name/inn/kpp/director_full_name/address }}` —
  и то же для `{{ executor.* }}`
- `{{ object.name/address/responsible_face/responsible_faces_contact }}`
- `{{ user.full_name }}`, `{{ user.role_name }}`
- `{{ today_long }}` (например «05 августа 2026 г.»)
- Nested `{%tr for group in equipment_groups %}` +
  `{%tr for row in group.rows %}` — многоуровневая таблица
  оборудования с нумерацией «1.», «1.1», «1.2», «2.», «2.1»

Отличия шаблонов:
- **planned.dotx** — Акт планового ТО с полной таблицей оборудования.
- **maintenance.docx** — Акт технического обслуживания (упрощённее,
  с исполнителем работ `{{ user.full_name }}`).
- **emergency.docx** — Акт аварийно-восстановительных работ, без
  таблицы оборудования, акцент на описании проблемы.
- **primary.dotx** — Акт первичного осмотра, с составом комиссии и
  таблицей найденного оборудования.

### Added — `scripts/generate_demo_templates.py`
Скрипт-генератор через `python-docx`. Каждый Jinja-плейсхолдер
пишется одним `run.add_text(...)` — Word не разбивает разметку на
несколько runs (в этом главная сложность ручной правки в Word).

Про nested-таблицу: `{%tr for %}` и `{%tr endfor %}` **целиком
удаляют содержащую строку таблицы** после парсинга. Для 2-уровневого
цикла нужно 6 строк: header + open-outer + group-row + open-inner
+ item-row + close-inner + close-outer. Иначе таблица рендерится
пустой.

### How to apply
- Локально: `python scripts/generate_demo_templates.py` перезаписывает
  4 файла в `templates/seeds/`.
- В контейнере demo: после fan-out нужно повторить seed_demo
  (он копирует шаблоны в MEDIA), либо ждать ежесуточного restore
  из эталона (D5).

VERSION 1.0.41 → 1.0.42.

## [1.0.41] — 2026-09-07

### Fixed
- `scripts/seed_demo.py`: при повторном запуске падал с
  `UniqueViolationError: Key (code)=(planned) already exists`.
  Причина — Alembic-миграция `f5d8a2c1e9b4` сидит 3 системных
  `spec_orders` (emergency/primary/planned) с именами «Аварийная»/
  «Первичная»/«Плановая ТО» и `is_system=True`. Мой seed_demo искал
  по `name='Плановое ТО'` — не находил — пытался INSERT — конфликт
  по уникальному `code`.
- Fix: искать по `code` (уникальный ключ), при находке обновлять
  `name/short_name/template_*/sla_*`, `is_system` не трогать.

VERSION 1.0.40 → 1.0.41.

## [1.0.40] — 2026-09-07

### Changed — `scripts/seed_demo.py` (D1+ демо-стенда): шаблоны и типы заявок
Расширил seed_demo, чтобы на demo-тенанте работала кнопка «Скачать акт»
и были реальные шаблоны актов/журналов, а не пустой каталог.

- **Копирование `.docx/.dotx` шаблонов**. Функция `copy_seed_templates()`
  берёт файлы из `templates/seeds/` и **перезаписывает** их в
  `MEDIA_TEMPLATES_PATH` (в отличие от `scripts/seed_templates.py`,
  который skip'ает существующие — там защита прод-загрузок админа,
  здесь эталон должен строго соответствовать репе).
- **4 типа заявок** вместо одного «Плановое ТО». Каждый привязан к
  своему шаблону (`template_storage_path` = `templates/<file>`):
    - «Плановое ТО» (planned.dotx, sla_kind=periodic)
    - «Обслуживание» (maintenance.docx, sla_kind=periodic)
    - «Аварийная заявка» (emergency.docx, sla_kind=from_creation,
      sla_days=3)
    - «Первичный осмотр» (primary.dotx, sla_kind=manual)
- **50 заявок round-robin** по 4 типам. Префикс в номере тоже
  меняется — ППР-.../ТО-.../АВР-.../ПО-... — визуально видно, что
  каталог типов работает.
- **2 типа журналов** через `Spec_Journal`: «Журнал технического
  обслуживания» и «Журнал первичного осмотра». Без шаблонов пока —
  посетитель может загрузить свой .docx через UI и увидеть работающий
  флоу генерации журнала.

### Note
`Spec_Journal` не экспортируется в `model/__init__.py`, поэтому
импорт через `from model.spec_journal import Spec_Journal` напрямую.
Стоит перенести в `__init__.py` при ближайшей уборке модели.

### Deploy notes
- Скрипт идемпотентен для новых прогонов на **чистой** БД.
- Если demo-тенант уже сидился первой версией скрипта (v1.0.39),
  повторный прогон обновит spec_order (добавит template_*, sla_*),
  но существующие 50 заявок так и останутся привязанными к planned.
  Правильный порядок перед D4 (dump эталона): чистая БД + свежий
  прогон seed_demo:
  ```bash
  docker exec postgres-demo psql -U autoreport -d autoreport \
      -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
  docker restart backend-demo   # прокрутит alembic upgrade head
  docker exec backend-demo python scripts/seed_demo.py
  ```

VERSION 1.0.39 → 1.0.40.

## [1.0.39] — 2026-09-07

### Added — D1 демо-стенда: `scripts/seed_demo.py`
Скрипт наполнения демо-тенанта (`demo.cool-doc.ru`) правдоподобными
данными для публичной «примерки» сервиса. Первый шаг плана
[[autoreport-demo-stand]].

Что делает:
- Создаёт 2 роли **без superadmin**: «Администратор» (полный CRUD
  по всем сущностям и справочникам, `is_admin=True`) и «Менеджер»
  (read по операционной базе + create/modify для order/report/issue,
  без delete, без role/admin). Обе `is_protected=True` — чтобы
  демо-юзер не удалил их из UI. Полный чек-лист плоских флагов —
  в `DEMO_ROLE_ADMIN_PERMS` и `DEMO_ROLE_MANAGER_PERMS` (~110 строк).
- Создаёт 2 юзеров: `admin` и `manager`, пароль обоим `demo1234`
  (публичный, будет на лендинге). `is_protected=True` — защита от
  удаления через UI.
- Сеет справочники (регион / арэал / населённый пункт / улица /
  здание, банк, тип контракта, тип оборудования, spec_order, spec_status,
  spec_priority, период). По одной репрезентативной русскоязычной
  записи каждого — MVP; расширим когда данных станет мало.
- Берёт `is_default` из `spec_order_statuses` и `spec_report_statuses`
  (создаются Alembic-миграциями `a0b1c2d3e4f5` и `f3a4b5c6d7e8`
  соответственно). Если дефолт снят — скрипт падает с явным
  сообщением, а не тихо.
- 2 организации: «ООО Технопром» (заказчик) + «ООО Сервис-Про»
  (исполнитель).
- 10 договоров (Д-2026/001…010) с реалистичными предметами из
  landing showcase.
- 30 объектов (ЦОД «Северный», склад, насосная и т.п. — 30 шаблонов
  из `OBJECT_TEMPLATES`), round-robin по договорам.
- 20 типов оборудования (ИБП APC, кондиционеры Daikin/Mitsubishi,
  АВР, насосы Grundfos, чиллер Carrier, СКУД PERCo, лифт OTIS и т.п.).
- 120 связок object-equipment (4 единицы на каждый объект),
  идемпотентно через `UniqueConstraint(object_id, equipment_id)`.
- 50 заявок (ППР-08/2026/001…050), 20 отчётов, 10 неисправностей —
  с русскими названиями проблем.

**Идемпотентность**: все проверки через `_get_or_create` по `name`/
`number`. Повторный запуск обновляет флаги ролей (на случай если
чек-лист прав меняли в коде) и сбрасывает пароли юзеров, остальное
не трогает.

**Запуск (после D2 — провижна demo-тенанта):**
```bash
docker exec backend-demo poetry run python scripts/seed_demo.py
```

VERSION 1.0.38 → 1.0.39.

## [1.0.38] — 2026-09-06

### Fixed
- Создание второго отчёта по другой заявке на тот же объект в том же
  месяце возвращало 400 «Отчёт за MM.YYYY по объекту №N уже
  существует». Причина: `generated_number` для отчёта собирался как
  `{obj.n}/{MM}/{YYYY}/{customer}/{contract}` — без типа заявки и
  без счётчика. Аварийные (АВР) заявки создаются по потребности —
  их может быть несколько в месяц по одному объекту.
- Fix: добавили в маску `spec_order.short_name` + `seq` (порядковый
  номер отчёта такого же типа для объекта в месяц) —
  `{obj.n}/{MM}/{YYYY}/{customer}/{contract}/{spec_order}/{seq}`.
  Аналогично маске Order.number. seq считается через join Report←Order
  по `spec_order_id` и месяцу создания. Финальная защита от гонки
  остаётся (check_report_number_exists).
- Заодно service подгружает `order.spec_order` через selectinload
  вместе с `order.object` — чтобы избежать lazy-load после закрытия
  сессии.

## [1.0.37] — 2026-09-06

### Fixed
- `PATCH /api/report/{id}/status` возвращал 400 «Статус с id N не
  существует». Причина: `service.update_report_status` валидировал
  status_id через старую таблицу `spec_statuss` (это Issue.status_id),
  а не через `spec_report_statuses` (Report.status_id после миграции
  f3a4b5c6d7e8). Также docstring врал «FK на spec_statuss».
- Fix: замена `spec_status_data.get_spec_status_by_id` →
  `spec_report_status_data.get_spec_report_status_by_id`. Идёт в паре
  с Auto_report_front v1.0.32 (там фронт уже читает
  `/spec_report_status/options` и ищет по name === 'Утверждён').

## [1.0.36] — 2026-09-06

### Fixed
- PUT `/api/order/{id}` возвращал 500 при редактировании существующей
  заявки (изменение полей сохранялось в БД, но клиент видел ошибку).
  Причина: `DetachedInstanceError` при обращении к `order.id` в
  api/order.py:316. `service.update_order` после успешного апдейта
  делает `data.update_order` (session.commit → expire_on_commit=True),
  затем `log_activity` (ещё commit → снова expire) — по выходу из
  `async with new_session()` инстанс становится detached, любое
  чтение атрибута тригерит refresh, который падает.
- Fix: `service.update_order` теперь возвращает `int` (id заявки),
  а не ORM-инстанс. `api/order.py::update_order` использует этот id
  напрямую в вызове `get_order_with_details` (создаёт свою сессию).
  Атрибуты `order.id` и `order.number` для audit-summary захватываются
  в локальные переменные ПОКА сессия ещё активна.

## [1.0.35] — 2026-09-05

### Added — master-inbound endpoints для сброса пароля superadmin'а
- `GET /api/tenant/admins` — список активных superadmin юзеров тенанта
  (id, name, full_name, email, is_protected). Auth: тот же
  `MASTER_API_TENANT_TOKEN` что `/tech-logs`. Master-UI на admin.cool-doc.ru
  использует для селекта пользователя в модалке «Сбросить пароль».
- `POST /api/tenant/admins/{user_id}/reset-password` — генерит новый
  пароль (`secrets.token_urlsafe(12)`), обновляет `User.hash` через
  `get_password_hash` (bcrypt), отзывает все активные refresh-сессии
  юзера (`revoke_all_user_sessions`). Возвращает
  `{user_id, name, full_name, email, new_password, sessions_revoked}`.
  Master парсит `new_password`, шлёт email на `tenant.email`, ничего
  не сохраняет.
- 404 если `user_id` не superadmin или не существует. Only superadmin —
  чтобы через этот прокси-канал нельзя было сбросить пароль обычному
  пользователю (для обычных — /api/user/{id}/password обычным путём).

## [1.0.34] — 2026-09-05

### Added
- MobileOrderListItem дополнен полями `due_date`, `report_id`,
  `report_status_name` — для отрисовки due-date маркера в mobile-приложении
  (та же логика что в web: температурная шкала + отчётный маркер если
  есть отчёт). `data/mobile.py::get_orders_for_mobile` LEFT JOIN на
  Report + Spec_Report_Status. Идёт вместе с mobile-релизом v1.8.0.

## [1.0.33] — 2026-09-05

### Fixed
- Response dict в `service/spec_order.py` (3 места) и в `api/spec_order.py`
  (2 места — `/all` и `/create`) вручную формировался БЕЗ полей
  `sla_kind/sla_days/sla_days_workdays`. Pydantic-схемы имеют defaults
  (`sla_kind='manual'`, остальные null/false), поэтому клиент получал
  `sla_kind='manual'` для ЛЮБОГО типа заявки, независимо от того что
  реально в БД. Симптом: при повторном открытии формы radio всегда на
  «Вручную», хотя PUT сохранил `periodic`/`from_creation` корректно.
  Добавил 3 поля во все 5 response dict'ов.

## [1.0.32] — 2026-09-05

### Fixed
- Поля `sla_kind`, `sla_days` отсутствовали в `schema/spec_order.py`
  (SpecOrderCreate/Update/Response) — PUT/POST через API их отсекал.
  Тип «Аварийная» в UI обновлялся, но настройки SLA (from_creation,
  sla_days=3) не сохранялись → у новых заявок этого типа
  `due_date=null`. Тот же паттерн что был с `schema/role.py`
  (v1.0.31). Добавил 3 поля + Literal-валидацию `SlaKind`.

### Added
- **Рабочие дни для SLA from_creation** — новое поле
  `Spec_Order.sla_days_workdays` (bool, default false).
  - Миграция `f6d7e8f9a0b1` — добавляет колонку.
  - `service/due_date.py::_add_workdays()` — прибавляет N рабочих
    дней (loop, пропускает сб/вс). Госпраздники не учитываются
    (простой вариант без внешнего справочника).
  - `compute_due_date()` — новый параметр `sla_days_workdays`.
  - Пример: пт 5 сен + 3 рабочих дня = ср 10 сен.
  - `service/order.py` create/update + `service/order_autogen.py`
    передают `spec_order.sla_days_workdays`.

## [1.0.31] — 2026-09-05

### Fixed
- Права `spec_report_status_*` не сохранялись при редактировании роли.
  В `schema/role.py::RoleBase` не хватало 4-х полей — PUT `/api/role/{id}`
  их отсекал (model_dump(exclude_unset=True) → пустой набор для этих
  полей → БД не обновлялась). Модель Role и миграция были ОК, только
  Pydantic-схема. Добавил 4 булевых поля с `default=False` — по образцу
  spec_order_status_*.

## [1.0.30] — 2026-09-05

### Fixed
- Hotfix после v1.0.29: 500 на GET /api/order/list и /api/order/my
  из-за `InvalidRequestError: 'Order.report' is not available due to
  lazy='raise'`. В `data/order.py` для списков стоял `raiseload(Order.report)`
  как защита от N+1, но новый сериализатор обращается к
  `item.report.status.name` для отчётного маркера. Заменил на
  `selectinload(Order.report)` в обоих местах (get_order_all + get_order_paginated).
  Report.status с `lazy="joined"` подтянется тем же SELECT'ом, N+1 не будет.

## [1.0.29] — 2026-09-05

### Added
- Due-date для заявок — Этап 2 (сервисный слой + API).
  - `service/due_date.py::compute_due_date()` — чистая функция расчёта
    срока по правилам Spec_Order (periodic → конец периода объекта,
    from_creation → created_at + sla_days, manual → None).
  - `service/order.py::create_order` — авто-заполняет `Order.due_date`
    если клиент не передал явно. Подгружает `Object.period` через
    selectinload для period_code.
  - `service/order.py::update_order` — при смене `spec_order_id`
    автоматически пересчитывает due_date (если клиент явно не переопределяет).
  - `service/order_autogen.py::_create_order` — авто-плановые/первичные
    заявки получают due_date по формуле.
  - `schema/order.py` — новые поля `due_date` в OrderCreate/OrderUpdate/
    OrderResponse/OrderListResponse + `report_status_name` в
    OrderResponse/OrderListResponse (для отчётного маркера во фронте).
  - `service/order.py` + `api/order.py` — dict-serializer'ы (детальный
    Order и списки) отдают `due_date` и `report_status_name`.
- Полный CRUD для `spec_report_statuses` (по образцу spec_order_statuses):
  `schema/data/service/api/spec_report_status.py`, роут
  `/api/spec_report_status/{options,list,create,{id},put,delete}`,
  RBAC-права `spec_report_status_*`. Правила is_default с partial
  unique index (нельзя снять/удалить дефолтную без переноса).

## [1.0.28] — 2026-09-05

### Fixed
- Отчёты — hotfix после v1.0.27: 500 на GET /api/report/list. Причина:
  много мест в service/data/api/schema ссылались на Spec_Status.code
  (у Report был FK на общий spec_statuss), но после переезда FK на
  spec_report_statuses (канонная схема без code) — `.status.code`
  выдавал AttributeError.
  - `schema/report.py` — убрал `status_code` из `ReportListResponse` и
    `ReportOptionResponse` (у нового справочника нет code, только name).
  - `data/report.py` — `get_spec_status_by_code(code)` заменён на
    `get_default_spec_report_status()` + `get_spec_report_status_by_name(name)`.
  - `service/report.py` — при создании отчёта берём is_default статус
    из spec_report_statuses (было — искали по code 'not_approved' и
    создавали Spec_Status на лету).
  - `service/report_attachment.py` — 3 места блокировки редактирования
    для approved отчёта (`report.status.code == 'approved'`) переведены
    на `report.status.name == 'Утверждён'`.
  - `api/report.py` — endpoint `/unapproved` теперь возвращает отчёты
    в статусе «На утверждении» (актуальная семантика для нового
    workflow «В работе → На утверждении → Утверждён/Отклонён»).

## [1.0.27] — 2026-09-05

### Added
- Due-date для заявок (Этап 1 — модели + миграции). Реализация в
  service/API — следующим коммитом.
  - `Spec_Order.sla_kind` (periodic / from_creation / manual) + `sla_days`
    — определяет как считать `Order.due_date` для заявок этого типа.
    Backfill: is_default_planned → periodic, is_default_primary →
    from_creation с sla_days=3 (АВР 3 дня по-умолчанию), остальные →
    manual. CHECK-констрейнты на валидность.
  - `Order.due_date` (DATE, nullable). Backfill открытых заявок
    (report_id IS NULL) по формуле от sla_kind типа + period_code
    объекта. Миграция считает конец календарного периода в Python
    (monthrange), обновляет по одной строке.
- Новый справочник `spec_report_statuses` с 4 сидовыми строками:
  «В работе» (default), «На утверждении», «Утверждён», «Отклонён».
  Канонная схема из 4 полей (id/name/description/is_default), partial
  unique на is_default = true. `Report.status_id` FK переведён с
  общего spec_statuss на новый спец-справочник; backfill всех
  существующих отчётов → default («В работе»).
- Роль: 4 новых RBAC-флага `spec_report_status_read/create/modify/delete`
  (по образцу `spec_order_status_*`). Superadmin — все, admin — READ.

### Migrations
- f3a4b5c6d7e8 — spec_report_statuses + сид 4 строк.
- f4b5c6d7e8f9 — role: 4 флага spec_report_status_*.
- f5c6d7e8f9a0 — Spec_Order SLA-поля + Order.due_date + Report.status_id
  FK на spec_report_statuses (backfill открытых заявок + всех отчётов).

## [1.0.26] — 2026-08-28

### Changed
- `UserResponse.role` теперь `RoleResponse` вместо `RoleSimpleResponse` —
  в него отдаются ВСЕ флаги прав (user_read/user_modify/…/spec_*).
  Нужно для UserDetailView во фронте, который рисует раскладку прав
  по группам PERMISSION_GROUPS. `RoleSimpleResponse` содержит только
  id/name/is_admin/is_superadmin/is_protected — не хватало.

## [1.0.25] — 2026-08-28

### Fixed
- **`GET /api/user/{user_id}`** — эндпоинт не существовал (были только
  `/list`, `/create`, `PUT/DELETE/{id}`, `/{id}/revoke-all-sessions`).
  Новый UserDetailView во фронте v1.0.16 падал с 405 Method Not
  Allowed при вызове `userStore.fetchById(id)`. Добавлен GET-обработчик
  с RBAC-проверкой `user_read | is_admin | is_superadmin`. Через
  `data.get_user_by_id`.

## [1.0.24] — 2026-08-28

### Added — Mobile QR-onboarding на стороне tenant'а (Этап 1 из плана)
- **`POST /api/user/{id}/mobile-onboard-token`** — админ выдаёт QR/ссылку
  для входа юзера в мобильное приложение. Требует новое право
  `Role.user_onboard_mobile` (см. миграцию), либо `is_admin`/`is_superadmin`.
- **`POST /api/user/me/mobile-onboard-token`** — self-service: юзер сам
  выпускает себе QR (например, поменял телефон). Без дополнительных прав.
- `service/mobile_onboard.py` — порт логики из
  `Auto_Report_Master/api/tenant.py::mint_mobile_onboard_token`.
  Подпись HS256 `MOBILE_ONBOARD_SECRET` (уже прописан в `.env` каждого
  tenant'а через `provision-tenant.sh`), PNG QR через `qrcode`.
  Валидатор — юзер существует, активен, не superadmin.
- `schema/role.py` + `model/role.py`: новый флаг `user_onboard_mobile`
  (default False). Миграция `e2b3c4d5f6a7` — backfill `TRUE` для
  `is_admin=True` и `is_superadmin=True` ролей.
- Master-эндпоинт `POST /api/tenants/{slug}/mobile-onboard-token`
  остаётся временно как fallback (будет удалён Этапом 4 плана).

## [1.0.23] — 2026-08-27

### Changed
- **`PUT /api/order/{id}`**: снято ограничение «менять только свои
  заявки» (403 если `existing.user_id != current_user.id and not
  is_admin`). Роль всё ещё проверяется через `order_modify`
  (`check_permission` выше). Причина: параллельный
  `POST /api/order/bulk_assign` (v1.0.21) с тем же RBAC уже работает
  по всем заявкам без учёта авторства, одиночный PATCH был единственным
  местом с рудиментом «только автор». Менеджер теперь может менять
  ответственного/статус в любой заявке через веб-форму как и через
  массовое назначение.

  `update_order_status` и `delete_order` — сохранили «только свои»,
  это отдельная семантика (статус двигает исполнитель, удаляет
  автор/админ).

## [1.0.22] — 2026-08-27

### Fixed
- **Hotfix v1.0.20 → падал на старте:**
  `sqlalchemy.exc.AmbiguousForeignKeysError: … relationship User.orders —
  there are multiple foreign key paths linking the tables`. Причина:
  у `Order` две FK на `users.id` (`user_id` — автор, `assigned_to_id` —
  ответственный), а обратная связь `User.orders` не указывала
  `foreign_keys=` и SQLAlchemy не мог понять по какой FK'ой матчить.
  Добавлен `foreign_keys="Order.user_id"` в `User.orders`.

## [1.0.21] — 2026-08-27

### Added
- **`POST /api/order/bulk_assign`** — массовое проставление
  ответственного за N заявок за один запрос. Body:
  `{order_ids: [1,2,3], assigned_to_id: 42}` или
  `{order_ids: [...], assigned_to_id: null}` (снять). Ответ:
  `{updated: <int>}`. RBAC: `order_modify`. Один агрегированный
  activity_log с полным списком id в details.

## [1.0.20] — 2026-08-27

### Added
- **`orders.assigned_to_id`** — новое поле «ответственный» (nullable FK на
  `users.id`, ondelete=SET NULL). Отдельно от `user_id` (АВТОР создания).
  Миграция `d1a2b3c4e5f6`. Проставляется через веб-UI при create/PATCH
  Order; у существующих заявок = NULL, backfill не делается.
- `model.Order.assigned_to` relationship (`lazy="joined"`, отдельные
  `foreign_keys` для обоих User-relationship'ов).
- `schema.OrderCreate/OrderUpdate` — поле `assigned_to_id`. В PATCH `0`
  или `null` = «снять ответственного» (service нормализует в NULL).
- `schema.OrderResponse/OrderListResponse` — `assigned_to_id` +
  `assigned_to_name` в ответах.
- Фильтр `assigned_to_id` в `/api/order/list` (0 = «без ответственного»).

### Changed
- **`/api/mobile/orders?only_mine=true`** теперь фильтрует по
  `Order.assigned_to_id == current_user.id`, а не по `Order.user_id`
  (там был АВТОР). Инженер видит «Мои» как заявки, которые ему
  назначили. `MobileOrderListItem.assigned_to_name` теперь честно
  берёт имя ответственного (join на User через assigned_to_id) — ранее
  колонка называлась «assigned_to_name», но join был через user_id
  (АВТОР), значение лгало. **Смок:** пока у Order.assigned_to_id везде
  NULL, «Мои» в mobile будет пустой → веб-CRUD должен проставить.

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
