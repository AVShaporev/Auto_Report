"""
Отправка push-уведомлений через Firebase Cloud Messaging (Mobile M7).

Полный дизайн: docs/PUSH_NOTIFICATIONS.md.

Feature-flag: если FCM_SERVICE_ACCOUNT_PATH не задан или файл отсутствует —
модуль стартует в no-op режиме: `init_fcm()` пишет warning, все send_*
функции возвращают 0 без исключений. Это позволяет раскатить код на
все tenant'ы, а активировать доставку по мере настройки Firebase.

Никакие push-фейлы (сеть/квоты/битые токены) не должны ломать основной
handler — все исключения ловятся здесь и уходят в лог. При ошибке для
конкретного токена «UNREGISTERED» — деактивируем токен в БД (юзер
удалил приложение или отозвал разрешения).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from data import push_token as push_token_data
from model.push_token import PushToken

# firebase-admin импортируется лениво — если пакет ставили без dev-deps
# или пропустили `poetry install`, обычный CRUD не должен падать на import'е.
_fcm_ready: bool = False
_fcm_messaging = None  # firebase_admin.messaging module после init'а


def init_fcm() -> bool:
    """
    Инициализация Firebase Admin SDK.
    Вызывается один раз при старте приложения (lifespan в main.py).

    Возвращает True если Firebase готов отправлять, False если no-op.
    """
    global _fcm_ready, _fcm_messaging

    # Приоритет 1: JSON целиком в env (удобно для SOPS).
    json_str = settings.FCM_SERVICE_ACCOUNT_JSON
    path_str = settings.FCM_SERVICE_ACCOUNT_PATH

    if not json_str and not path_str:
        logger.info(
            "[push] disabled: FCM_SERVICE_ACCOUNT_JSON / _PATH not set"
        )
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except ImportError:
        logger.error(
            "[push] disabled: firebase-admin not installed. "
            "Run `poetry install` or add `firebase-admin` to pyproject.toml."
        )
        return False

    cred = None
    source_desc = ""
    if json_str:
        try:
            sa_dict = json.loads(json_str)
            cred = credentials.Certificate(sa_dict)
            source_desc = f"env FCM_SERVICE_ACCOUNT_JSON (project={sa_dict.get('project_id', '?')})"
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                f"[push] disabled: FCM_SERVICE_ACCOUNT_JSON is not valid "
                f"JSON — {exc}"
            )
            return False
    else:
        path = Path(path_str)
        if not path.exists():
            logger.warning(
                f"[push] disabled: FCM_SERVICE_ACCOUNT_PATH={path_str} does not exist"
            )
            return False
        try:
            cred = credentials.Certificate(str(path))
            source_desc = f"file {path}"
        except Exception as exc:
            logger.error(f"[push] disabled: failed to load {path} — {exc}")
            return False

    try:
        options = {}
        if settings.FCM_PROJECT_ID:
            options["projectId"] = settings.FCM_PROJECT_ID
        # Idempotent: если уже инициализировано (например, тест повторно
        # зовёт init_fcm) — Firebase Admin бросит ValueError, ловим.
        try:
            firebase_admin.initialize_app(cred, options)
        except ValueError as e:
            if "already exists" not in str(e).lower():
                raise
        _fcm_messaging = messaging
        _fcm_ready = True
        logger.info(f"[push] enabled: firebase-admin loaded from {source_desc}")
        return True
    except Exception as exc:
        logger.error(f"[push] disabled: failed to initialize firebase — {exc}")
        _fcm_ready = False
        return False


async def send_assignment_notification(
    session: AsyncSession,
    *,
    user_id: int,
    entity: str,           # 'order' | 'issue'
    entity_id: int,
    entity_number: str,    # 'ЗА-2026-00042'
    title: str,
    body: str,
    route: str,            # '/orders/42' | '/issues/7'
) -> int:
    """
    Отправить push всем active-токенам юзера. Возвращает число успешно
    доставленных (0..N).

    См. docs/PUSH_NOTIFICATIONS.md § 2.3.
    """
    if not _fcm_ready or _fcm_messaging is None:
        # No-op режим. Не считаем это ошибкой — просто нет доставки.
        return 0

    tokens = await push_token_data.list_push_tokens_for_user(
        session, user_id, active_only=True
    )
    if not tokens:
        logger.info(f"[push] no active tokens for user_id={user_id}")
        return 0

    # firebase-admin — sync SDK, не хотим блокировать event-loop.
    # Оффлоадим в threadpool через run_in_executor.
    loop = asyncio.get_running_loop()
    delivered = await loop.run_in_executor(
        None,
        _send_multicast_sync,
        tokens,
        title,
        body,
        {
            "route": route,
            "entity": entity,
            "entity_id": str(entity_id),
            "entity_number": entity_number,
        },
    )

    # Деактивируем токены, которые FCM пометил invalid/unregistered.
    invalid_tokens: list[str] = []
    if delivered is not None:
        _, invalid_tokens = delivered
        for tok in invalid_tokens:
            for pt in tokens:
                if pt.token == tok:
                    pt.is_active = False
                    session.add(pt)
                    break
        if invalid_tokens:
            await session.commit()
            logger.info(
                f"[push] deactivated {len(invalid_tokens)} stale token(s) "
                f"for user_id={user_id}"
            )

    delivered_count = delivered[0] if delivered else 0
    logger.info(
        f"[push] user_id={user_id} entity={entity}#{entity_id} "
        f"delivered={delivered_count}/{len(tokens)}"
    )
    return delivered_count


def _send_multicast_sync(
    tokens: list[PushToken],
    title: str,
    body: str,
    data: dict[str, str],
) -> tuple[int, list[str]]:
    """
    Sync-часть, вызывается из executor. Возвращает (delivered_count,
    invalid_token_strings). Ошибки НЕ бросает — только логгирует.
    """
    if _fcm_messaging is None:
        return 0, []

    messaging = _fcm_messaging
    tok_strs = [pt.token for pt in tokens]

    try:
        message = messaging.MulticastMessage(
            tokens=tok_strs,
            notification=messaging.Notification(title=title, body=body),
            data=data,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="assignments",
                    sound="default",
                ),
            ),
        )
        response = messaging.send_each_for_multicast(message)
    except Exception as exc:
        logger.error(f"[push] fcm error: {exc}")
        return 0, []

    invalid: list[str] = []
    for idx, resp in enumerate(response.responses):
        if resp.success:
            continue
        err = resp.exception
        err_code = getattr(err, "code", "") or ""
        # Firebase code'ы для «мёртвых» токенов — деактивировать в БД.
        # Список кодов из firebase-admin SDK: UNREGISTERED, INVALID_ARGUMENT,
        # SENDER_ID_MISMATCH — все они означают что токен больше не работает.
        if err_code in (
            "UNREGISTERED",
            "INVALID_ARGUMENT",
            "SENDER_ID_MISMATCH",
        ):
            invalid.append(tok_strs[idx])
        else:
            # Прочие ошибки (QuotaExceeded, Unavailable) — retriable,
            # но retry-логику пока не делаем: пропустим этот вызов.
            logger.warning(
                f"[push] delivery failed for token={tok_strs[idx][:12]}…: "
                f"{err_code} — {err}"
            )

    return response.success_count, invalid


def is_ready() -> bool:
    """Есть ли рабочее Firebase-подключение. Для тестов / health-check'ов."""
    return _fcm_ready
