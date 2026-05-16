import time
from datetime import datetime
from typing import Optional

from jose import jwt
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config import settings
from utils.json_logger import current_user_var, json_logger


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
            logger.info(f"{request.method} {request.url.path} - {status_code} - {duration:.3f}s")
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
                })
            except Exception as e:
                logger.warning(f"JSON-лог HTTP не записан: {e!r}")
            current_user_var.reset(marker)
