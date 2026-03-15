import time
import asyncio
from functools import wraps
from loguru import logger

def timer(func):
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            start_str = time.strftime('%H:%M:%S', time.localtime(start))
            logger.info(f"[{start_str}] Начало выполнения {func.__name__}")

            result = await func(*args, **kwargs)

            end = time.perf_counter()
            end_str = time.strftime('%H:%M:%S', time.localtime(end))
            elapsed = end - start
            logger.info(f"[{end_str}] Конец выполнения {func.__name__} (затрачено: {elapsed:.4f} с)")
            return result
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            start_str = time.strftime('%H:%M:%S', time.localtime(start))
            logger.info(f"[{start_str}] Начало выполнения {func.__name__}")

            result = func(*args, **kwargs)

            end = time.perf_counter()
            end_str = time.strftime('%H:%M:%S', time.localtime(end))
            elapsed = end - start
            logger.info(f"[{end_str}] Конец выполнения {func.__name__} (затрачено: {elapsed:.4f} с)")
            return result
        return sync_wrapper