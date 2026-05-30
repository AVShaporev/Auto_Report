import time
from datetime import datetime
from typing import Optional

from jose import jwt
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config import settings
from utils.json_logger import current_user_var, json_logger
from utils import sql_counter


def _extract_username(request: Request) -> Optional[str]:
    """Декодирует Bearer-токен и достаёт sub (имя пользователя).
    Подпись/срок проверяет, но если что-то пошло не так — молча возвращает None;
    реальная валидация всё равно в FastAPI-депенде. Здесь нужно только для логов."""
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None


class LogRequestsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        username = _extract_username(request)
        marker = current_user_var.set(username)
        sql_counter.reset()
        started_at = datetime.now()
        start = time.perf_counter()
        status_code: Optional[int] = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            ended_at = datetime.now()
            duration = time.perf_counter() - start

            sql_snap = sql_counter.snapshot()
            sql_count = sql_snap["count"] if sql_snap else 0
            sql_time = sql_snap["total_time_sec"] if sql_snap else 0.0
            sql_suffix = f" | SQL: {sql_count} queries, {sql_time:.3f}s" if sql_snap else ""

            logger.info(
                f"{request.method} {request.url.path} - {status_code} - "
                f"{duration:.3f}s{sql_suffix}"
            )

            # Если запросов подозрительно много — дампим топ-5 для диагностики N+1
            top_queries = None
            if sql_snap and sql_snap["count"] >= 20:
                top_queries = sql_snap["queries"].most_common(5)
                logger.warning(
                    f"⚠ Подозрение на N+1: {sql_count} SQL за один запрос. Топ-5:"
                )
                for q, n in top_queries:
                    logger.warning(f"   {n}× {q}")

            try:
                json_logger.write({
                    "kind": "http",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "user": username,
                    "started_at": started_at.isoformat(),
                    "ended_at": ended_at.isoformat(),
                    "duration_sec": round(duration, 4),
                    "sql_count": sql_count,
                    "sql_time_sec": round(sql_time, 4),
                    "sql_top": [{"sql": q, "count": n} for q, n in (top_queries or [])] or None,
                })
            except Exception as e:
                logger.warning(f"JSON-лог HTTP не записан: {e!r}")
            current_user_var.reset(marker)
