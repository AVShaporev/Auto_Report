# Push-уведомления AutoReport Mobile — как это работает

_Дизайн-документ. Актуально с v1.0.45 backend + v1.7.11 mobile
(2026-09-13). При изменении логики — синхронизировать этот файл в
одном коммите с кодом (правило [feedback-autoreport-docs-sync])._

Цель: инженер, назначенный на заявку/неисправность, узнаёт о новой
работе **мгновенно** через системное уведомление на телефон, без
необходимости самому открывать приложение и обновлять список.

---

## TL;DR (карта того, что происходит)

```
                    ┌──────────────────────────────────────────────┐
                    │ Диспетчер меняет assigned_to_id заявки в web │
                    └───────────────────┬──────────────────────────┘
                                        │  PUT /api/order/{id}
                                        ▼
     ┌──────────────────────────────────────────────────────────────┐
     │ Auto_Report backend                                          │
     │  service/order.update_order → detect change of assigned_to_id│
     │       │                                                      │
     │       └─► service/push.send_assignment_notification(         │
     │                user_id=new_assignee,                         │
     │                entity='order', entity_id=..., title=..., ...)│
     └───────────────────┬──────────────────────────────────────────┘
                         │  1. читает push_tokens по user_id
                         │  2. составляет FCM data-message
                         │  3. HTTP POST к Firebase Cloud Messaging
                         ▼
     ┌──────────────────────────────────────────────────────────────┐
     │ FCM (Google)                                                 │
     │  ├── доставка на Android-устройства                          │
     │  └── возврат статусов доставки (invalid tokens → deactivate) │
     └───────────────────┬──────────────────────────────────────────┘
                         │  Native push
                         ▼
     ┌──────────────────────────────────────────────────────────────┐
     │ Auto_Report_Mobile (Capacitor APK)                           │
     │  1. `pushNotificationReceived` → toast/banner в UI           │
     │  2. `pushNotificationActionPerformed` (тап) → router.push(   │
     │                 data.route) — /orders/123 или /issues/45     │
     └──────────────────────────────────────────────────────────────┘
```

Стек: **Firebase Cloud Messaging (FCM)** — Google's push-service.
Работает на всех Android-устройствах (нативные Google Services), в
iOS-версии в будущем будет проксировать через APNs (Apple), но пока
iOS не собираем — фокус на Android APK.

---

## Часть 1. Prerequisites (единоразовая настройка Firebase)

**Кто делает:** юзер (Андрей). AI не может это автоматизировать —
Firebase Console закрыт капчей и требует Google-аккаунта.

### 1.1. Создать Firebase-проект
1. Открыть [console.firebase.google.com](https://console.firebase.google.com/).
2. `Add project` → название `AutoReport-Prod` (для VDS-prod) или
   `AutoReport-Stage` (для 192-stage — опционально, можно тестить
   на одном prod-проекте).
3. Google Analytics — можно отключить, не нужно.
4. Проект создался.

### 1.2. Зарегистрировать Android-приложение
1. В проекте — «+ Add app» → выбрать Android.
2. Package name: **`com.coolcoc.autoreport`** (значение из
   `Auto_Report_Mobile/android/app/build.gradle` → `applicationId`;
   уточнить актуальный, если менялся).
3. Nickname: `AutoReport Mobile Android`.
4. Debug signing certificate SHA-1: пропустить (для release-сборки
   в будущем — надо будет добавить).
5. Скачать **`google-services.json`** — Firebase его сгенерирует
   после регистрации приложения.

### 1.3. Положить `google-services.json` в mobile-репо
```
Auto_Report_Mobile/android/app/google-services.json
```
Этот файл содержит `project_id`, `api_key`, `app_id` — **не секрет,
но и не совсем публичный** (даёт возможность отправлять неавторизованные
push-запросы если использовать SDK). Достаточно приватный чтобы
не публиковать на GitHub — держим в `.gitignore` + отдельно раздаём
через SOPS или CI-artifact. Пока — **храним в git** (риск малый,
т.к. FCM-endpoint по прежнему требует server-key со стороны бэка).
Позже переедет в SOPS-encrypted, если станет чувствительным.

### 1.4. Сгенерировать Service Account для backend
Backend отправляет push через **Firebase Admin SDK** — ему нужен
приватный ключ с service-account'а.

1. В Firebase Console → Project settings → Service accounts.
2. `Generate new private key` — скачается **`fcm-service-account.json`**
   с полями `project_id`, `private_key`, `client_email` и т.д.
3. Этот файл — **секрет**. Никогда не в git.

### 1.5. Добавить путь к service-account'у в SOPS-env бэка
Для каждого tenant (`backend-<slug>`) в `deploy/secrets/<env>.env.sops`
(SOPS-encrypted):

```env
# Firebase Cloud Messaging (Mobile M7)
FCM_SERVICE_ACCOUNT_PATH=/app/secrets/fcm-service-account.json
```

Файл `fcm-service-account.json` монтируется в контейнер через
Docker-secret или volume: `docker-compose` → `secrets: fcm_sa` → mount
в `/app/secrets/fcm-service-account.json`.

**Feature-flag:** если `FCM_SERVICE_ACCOUNT_PATH` не задан или файл
отсутствует — backend всё равно стартует, но `service/push.py` в
режиме no-op (лог `[warn] FCM disabled: no service account`, все
`send_*`-функции возвращают `False` без исключений). Это позволяет
раскатить код на все tenant'ы, а активировать только тем, у кого
Firebase уже настроен.

---

## Часть 2. Backend — как отправляется push

### 2.1. Инфра, которая уже есть (M1.2 → v1.0.44)
- Модель [`model/push_token.py`](../model/push_token.py) — таблица
  `push_tokens` с (user_id, platform, token, device_id, app_version,
  last_seen_at, is_active).
- DAO [`data/push_token.py`](../data/push_token.py) —
  `list_push_tokens_for_user`, `upsert_push_token`, `delete_push_token`,
  `cleanup_stale_push_tokens`.
- API [`api/user.py`](../api/user.py) — `POST/GET/DELETE /api/user/me/push-token`.
- APScheduler cleanup @03:15 МСК — сносит `last_seen_at < NOW-30d`.

### 2.2. Что добавляется в M7 → v1.0.45
- **`service/push.py`** — единая точка отправки. Клиент FCM,
  формирование payload, обработка ошибок доставки.
- **Триггеры в `service/order.py`** — при create/update заявки, если
  `assigned_to_id` появился/изменился → зовём `push`.
- **Триггеры в `service/issue.py`** — аналогично для неисправностей
  (assigned_to_id).
- Poetry-dep: `firebase-admin ~= 6.5`.

### 2.3. API `service/push.py`

Публичный интерфейс:

```python
async def send_assignment_notification(
    session: AsyncSession,
    *,
    user_id: int,
    entity: Literal['order', 'issue'],
    entity_id: int,
    entity_number: str,        # 'ЗА-2026-00042' или 'INC-2026-00007'
    title: str,                # заголовок push'а
    body: str,                 # текст push'а
    route: str,                # '/orders/42' или '/issues/7' — deep-link
) -> int:
    '''
    Отправляет push на все active-токены юзера. Возвращает число успешно
    доставленных (0..N).

    Ошибки FCM:
      - InvalidArgument / Unregistered → токен «мёртвый» (юзер удалил
        приложение или сбросил разрешения) → is_active=false в БД.
      - QuotaExceeded / Unavailable → retriable, но не блокируем
        вызывающий handler — пишем в лог, идём дальше.

    Не бросает исключений вверх — push-фейл не должен ломать PUT
    /order/{id}. Ошибки только в лог.
    '''
```

Внутри — читает `list_push_tokens_for_user(session, user_id)`,
для каждого токена формирует FCM-message:

```json
{
  "token": "eXXXX...",
  "notification": {
    "title": "Новая заявка",
    "body": "Заявка ЗА-2026-00042 — Замена клапана на объекте «БЦ Радуга»"
  },
  "data": {
    "route": "/orders/42",
    "entity": "order",
    "entity_id": "42",
    "entity_number": "ЗА-2026-00042"
  },
  "android": {
    "priority": "HIGH",
    "notification": {
      "channel_id": "assignments",
      "sound": "default"
    }
  }
}
```

Отправка через `firebase_admin.messaging.send()` (или `send_multicast()`
если ≥ 2 токена у юзера — экономит round-trips).

### 2.4. Триггеры

**Order — `service/order.py::update_order`:**
```python
async def update_order(session, order_id, payload, ...):
    old_assignee = order.assigned_to_id
    # ... применяем payload ...
    new_assignee = order.assigned_to_id
    await session.commit()

    if new_assignee and new_assignee != old_assignee:
        await push.send_assignment_notification(
            session,
            user_id=new_assignee,
            entity='order',
            entity_id=order.id,
            entity_number=order.number,
            title='Новая заявка',
            body=f'Заявка {order.number} — {order.description[:80] or order.spec_order.name}',
            route=f'/orders/{order.id}',
        )
    return order
```

**Order — `service/order.py::create_order`:** аналогично, если сразу
создали с `assigned_to_id` — шлём push сразу после commit'а.

**Issue — `service/issue.py::update_issue` / `create_issue`:**
идентичный паттерн, только entity='issue', route='/issues/{id}',
title='Новая неисправность на вас'.

**Что важно:**
- Пуш идёт **после commit'а транзакции**, а не внутри. Иначе может
  прилететь push на заявку, которую тут же откатит race-condition.
- Пуш **не блокирует ответ HTTP**: `await` держим, но при таймауте FCM
  (≥ 5 сек) считаем failure и идём дальше — не заставляем пользователя
  ждать в UI.
- Юзер **не получает push, если сам себя назначает** (`current_user.id
  == new_assignee`) — избыточно, он и так знает.

### 2.5. Обработка invalid-токенов

FCM возвращает 4xx-коды для «мёртвых» токенов:
- `messaging/registration-token-not-registered` — приложение удалено /
  разрешения отозваны.
- `messaging/invalid-argument` — токен битый.

Оба случая — токен деактивируется в БД (`is_active=False`), а не
удаляется сразу. Через 30 дней APScheduler-cleanup их сам снесёт.

---

## Часть 3. Mobile — как принимается push

### 3.1. Инфра, которая уже есть (M1.2)
- `@capacitor/push-notifications` установлен.
- При логине — регистрация токена: `PushNotifications.requestPermissions()`
  → `.register()` → `token → POST /api/user/me/push-token`.
- На логауте — `DELETE /api/user/me/push-token`.

### 3.2. Что добавляется в M7 → v1.7.11
- Обработчик `pushNotificationReceived` — уведомление пришло, а
  приложение открыто (foreground). Показываем toast «Новая заявка на
  вас» с кнопкой «Открыть».
- Обработчик `pushNotificationActionPerformed` — юзер тапнул по
  уведомлению (foreground/background/quit). Читаем `data.route` →
  `router.push(route)`.
- Android notification channel `assignments` создаётся при первой
  регистрации — категория «Назначения», важность HIGH (пользователь
  видит в статус-баре + звук).

### 3.3. Код mobile-side (`src/services/push.js`)

Публичный интерфейс:
```js
export async function initPushHandlers(router) {
  await PushNotifications.addListener('pushNotificationReceived', (n) => {
    // foreground — показать toast
    toast.info(`${n.title || 'Уведомление'}: ${n.body || ''}`)
  })
  await PushNotifications.addListener('pushNotificationActionPerformed', (a) => {
    const route = a?.notification?.data?.route
    if (route) router.push(route)
  })
}
```

Вызывается один раз в `main.js` после `createApp(...).use(router)`.

### 3.4. Разрешения

Android 13+ требует **явного запроса** разрешения на уведомления
(`android.permission.POST_NOTIFICATIONS`). До Android 13 — auto-grant.

Стратегия:
- При **логине** — запрашиваем permission. Если юзер отказал — токен
  не регистрируем, показываем в HomeView-баннер «Уведомления
  выключены, вы не увидите новые заявки» с кнопкой «Разрешить».
- Если юзер отзовёт разрешение позже — при следующем открытии
  приложения `checkPermissions()` вернёт `denied`, показываем тот же
  баннер.

### 3.5. Deep-link при холодном старте

Если push пришёл когда приложение закрыто → юзер тапнул → APK
запустился → в `main.js` до маунта роутера уже есть
pending-notification. Capacitor выдаёт её через
`PushNotifications.getDeliveredNotifications()` или через ранний
event `pushNotificationActionPerformed`. Мы вешаем listener **до
`app.mount()`** — Capacitor его буферизует и стреляет как только
listener есть.

Route применяется через `router.push(route)` уже после `.use(router)`.

---

## Часть 4. Как это тестировать

### 4.1. Локально (unit-level)

Backend: `pytest tests/test_push.py`:
- Мок `firebase_admin.messaging.send` → проверяем что payload
  формируется правильно.
- Мок invalid-token response → проверяем что `push_tokens.is_active`
  обновляется в False.
- Проверяем что self-assignment не шлёт push.

Mobile: смок с браузера бесполезен (нет Firebase на web). Только
физическое устройство с установленным APK.

### 4.2. E2E-smoke на 192-stage

1. Активировать Firebase на stage: положить `fcm-service-account.json`,
   прописать `FCM_SERVICE_ACCOUNT_PATH` в `.env.sops`, redeploy.
2. Собрать APK v1.7.11, установить на телефон.
3. Залогиниться как инженер (не суперадмин).
4. С другой сессии (диспетчер в web) создать заявку, назначить
   инженера. Ожидание — уведомление на телефоне за ≤ 3 сек.
5. Тап по уведомлению → должно открыть `/orders/{id}` в приложении.
6. Проверить логи `backend-<slug>` — должен быть `[push] sent 1/1 to
   user_id=X` или `[push] no active tokens for user_id=X` если юзер
   не подключил телефон.

### 4.3. Что смотрим при проблемах

- **Не пришёл push:** сначала `SELECT * FROM push_tokens WHERE
  user_id=X AND is_active=true` — если пусто, дело в токене
  (приложение не зарегистрировалось). Если строки есть — смотрим
  логи бэка на `[push] fcm error ...`.
- **Пришёл, но не открывает нужный экран:** проверить
  `data.route` в payload'е (можно `console.log` в
  `pushNotificationActionPerformed` handler'е).
- **Не запрашивает разрешение:** Android 13+ и юзер не залогинен —
  запрос идёт при логине, до этого — нет. Логиниться → снова
  вылезет системный prompt.

---

## Часть 5. Что НЕ делаем в M7 (осознанные ограничения)

- **iOS.** APNs требует Apple Developer Account ($99/год) и
  прошивки. Пока iOS-APK не собираем — отложено.
- **Уведомления не о назначении.** Смена статуса заявки, создание
  отчёта, комментарии — пока не шлём. Только assignment. Расширять
  в M8+.
- **Топики / broadcast.** Пока не нужны. Все уведомления —
  таргетированные по user_id.
- **UI-настройки «типы уведомлений».** Пока один тип «Назначения», в
  будущем можно добавить toggle'ы в SettingsView.
- **Уведомления заказчику** (о готовности отчёта). Идёт в связке с
  идеей mobile-версии для Заказчика (см.
  [[project-autoreport-future-ideas]] #2) — реализуем вместе с ней.

---

## Часть 6. Файлы, которые правит M7

Backend (Auto_Report):
- `pyproject.toml` — добавить `firebase-admin`.
- `config.py` — добавить `FCM_SERVICE_ACCOUNT_PATH` в settings.
- `service/push.py` — **новый**, основная логика.
- `service/order.py` — hook в create/update.
- `service/issue.py` — hook в create/update.
- `main.py` — инициализация Firebase Admin SDK при старте (если
  `FCM_SERVICE_ACCOUNT_PATH` задан).
- `docs/PUSH_NOTIFICATIONS.md` — **этот файл**.

Mobile (Auto_Report_Mobile):
- `src/services/push.js` — **новый**, инициализация listener'ов.
- `src/main.js` — импорт и вызов `initPushHandlers(router)`.
- `src/stores/authStore.js` — при логине запрос permission +
  регистрация токена (расширение существующего flow M1.2).
- `src/views/HelpView.vue` — раздел «Уведомления» (правило
  [feedback-autoreport-mobile-help-sync]).
- `android/app/build.gradle` — Firebase plugin.
- `android/app/google-services.json` — Firebase config (не секрет,
  но в git пока не публиковать).

---

## Часть 7. Rollout-план

1. **v1.0.45 backend + v1.7.11 mobile** — код в stage, но FCM
   deactivated (нет service-account.json). Никаких push'ей не
   уходит, всё работает как раньше.
2. Юзер настраивает Firebase (см. Часть 1), кладёт JSON'ы, обновляет
   SOPS.
3. Redeploy stage → smoke по Части 4.2.
4. Merge stage → prod в обоих репо.
5. Fan-out через `redeploy-tenants.sh` — все существующие tenant'ы
   получают код. Firebase-key раскатывается tenant-by-tenant через
   обновление SOPS-env каждого.
6. Собираем и раздаём APK v1.7.11 инженерам, они логинятся — токены
   регистрируются автоматически.

---

## Приложение А. Формат FCM-payload

Что реально уходит в HTTP-запросе к
`https://fcm.googleapis.com/v1/projects/<PROJECT_ID>/messages:send`
(SDK обёртывает эту логику, показываем для отладки):

```http
POST https://fcm.googleapis.com/v1/projects/autoreport-prod/messages:send
Authorization: Bearer <access_token>   ← из service_account через SDK
Content-Type: application/json

{
  "message": {
    "token": "eXXXX...",
    "notification": {
      "title": "Новая заявка",
      "body": "ЗА-2026-00042 — Замена клапана на «БЦ Радуга»"
    },
    "data": {
      "route": "/orders/42",
      "entity": "order",
      "entity_id": "42",
      "entity_number": "ЗА-2026-00042"
    },
    "android": {
      "priority": "HIGH",
      "notification": {
        "channel_id": "assignments",
        "sound": "default",
        "click_action": "FLUTTER_NOTIFICATION_CLICK"
      }
    }
  }
}
```

Успех — `200 OK { "name": "projects/.../messages/<id>" }`.
Мёртвый токен — `404` c `error.details[].errorCode ==
"UNREGISTERED"` → деактивируем токен.
