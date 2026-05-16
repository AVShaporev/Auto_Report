import time
import asyncio
from datetime import datetime
from functools import wraps

from loguru import logger

from utils.json_logger import (
    current_user_var,
    extract_payload,
    json_logger,
)


def _emit(func, started_at: datetime, ended_at: datetime, duration: float, args: tuple, kwargs: dict) -> None:
    event = {
        "kind": "function",
        "function": func.__name__,
        "module": func.__module__,
        "user": current_user_var.get(),
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_sec": round(duration, 4),
    }
    payload = extract_payload(func.__name__, args, kwargs)
    if payload is not None:
        event["payload"] = payload
    try:
        json_logger.write(event)
    except Exception as e:
        logger.warning(f"JSON-лог функции не записан: {e!r}")


def timer(func):
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            started_at = datetime.now()
            start = time.perf_counter()
            logger.info(f"[{started_at.strftime('%H:%M:%S')}] Начало выполнения {func.__name__}")
            try:
                return await func(*args, **kwargs)
            finally:
                ended_at = datetime.now()
                duration = time.perf_counter() - start
                logger.info(f"[{ended_at.strftime('%H:%M:%S')}] Конец выполнения {func.__name__} (затрачено: {duration:.4f} с)")
                _emit(func, started_at, ended_at, duration, args, kwargs)
        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        started_at = datetime.now()
        start = time.perf_counter()
        logger.info(f"[{started_at.strftime('%H:%M:%S')}] Начало выполнения {func.__name__}")
        try:
            return func(*args, **kwargs)
        finally:
            ended_at = datetime.now()
            duration = time.perf_counter() - start
            logger.info(f"[{ended_at.strftime('%H:%M:%S')}] Конец выполнения {func.__name__} (затрачено: {duration:.4f} с)")
            _emit(func, started_at, ended_at, duration, args, kwargs)
    return sync_wrapper
