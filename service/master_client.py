"""HTTP-клиент к master-API (Auto_Report_Master).

Пока — только `fetch_lifecycle(slug)` для soft-mode банера (Этап 8.2).

Кэш в памяти на TTL секунд, чтобы:
1. не долбить master N раз в минуту при активном использовании UI фронтом;
2. если master временно недоступен — фронт видит последнюю успешную запись,
   а не сразу баннер пропадает.

Кэш — глобальный dict в модуле. Простое MVP: при рестарте backend'а сбрасывается,
для баннера ок. Если понадобится — заменить на Redis / TTL-cache библиотеку.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}
_CACHE_TTL_SECONDS = 5 * 60  # 5 минут — lifecycle меняется медленно
_HTTP_TIMEOUT_SECONDS = 5.0


class MasterUnavailable(RuntimeError):
    """Не получилось сходить в master — либо не сконфигурирован, либо сеть/HTTP fail."""


async def fetch_lifecycle(slug: str) -> dict[str, Any]:
    """Получить lifecycle-статус tenant'а из master-API.

    Кэшируется на _CACHE_TTL_SECONDS. При master-fail возвращает последнее
    успешное значение (если было в кэше) — фронт продолжает показывать
    актуальный минуту назад баннер вместо резкого исчезновения.

    Raises:
        MasterUnavailable — если master не сконфигурирован (нет URL/TOKEN)
            ИЛИ первый запрос упал (кэша ещё нет).
    """
    if not settings.MASTER_URL or not settings.MASTER_API_TENANT_TOKEN:
        raise MasterUnavailable("MASTER_URL или MASTER_API_TENANT_TOKEN не заданы")

    cache_key = slug
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached is not None:
        ts, value = cached
        if now - ts < _CACHE_TTL_SECONDS and value is not None:
            return value

    url = f"{settings.MASTER_URL.rstrip('/')}/api/lifecycle/{slug}"
    headers = {"Authorization": f"Bearer {settings.MASTER_API_TENANT_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        _CACHE[cache_key] = (now, data)
        return data
    except Exception as exc:
        logger.warning("master lifecycle fetch failed для slug=%s: %s", slug, exc)
        if cached is not None and cached[1] is not None:
            # Возвращаем stale-значение — лучше устаревшее, чем ничего.
            return cached[1]
        raise MasterUnavailable(str(exc)) from exc
