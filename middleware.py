import time
from datetime import datetime
from typing import Optional

from jose import jwt
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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


# Path'ы, для которых пропускаем JSONL-запись (не текстовый лог).
# Здоровье-чекa master-monitoring'а и внешних uptime-мониторов забивают
# логи и не несут диагностической ценности.
_JSONL_SKIP_PATHS = {"/api/health"}


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

            if request.url.path not in _JSONL_SKIP_PATHS:
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


# ============================================================================
# IdempotencyMiddleware — Mobile M1.4
# ============================================================================
# Mobile-клиент в поле теряет связь на середине POST/PUT/PATCH → ретаит
# запрос → без idempotency создаются дубли (заявка, отчёт).
#
# Клиент шлёт `X-Idempotency-Key: <uuid>`. Middleware:
#   1. если header отсутствует ИЛИ юзер не auth'ен → работаем как обычно.
#   2. если запись (user_name, key) в idempotency_keys есть и не просрочена
#      → возвращаем закэшированный ответ без вызова endpoint'а.
#   3. иначе — вызываем endpoint, если статус 2xx → сохраняем.
#
# Кэшируем 2xx только — 4xx клиенту стоит увидеть заново (например, 422 после
# правки формы), 5xx тоже дать шанс на новый успех.
#
# TTL 24 часа (fixed) — достаточно для «дневных» смен инженера.
_IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_IDEMPOTENCY_HEADER = "x-idempotency-key"
_IDEMPOTENCY_TTL_HOURS = 24


async def _read_body_bytes(response: Response) -> bytes:
    """Собрать body из StreamingResponse (что вернул FastAPI) в bytes.
    После этого нужно вернуть НОВЫЙ Response с этим body, иначе body_iterator
    уже exhausted."""
    body = b""
    async for chunk in response.body_iterator:
        body += chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
    return body


def _serializable_headers(headers) -> dict:
    """Только те заголовки, которые имеет смысл сохранить (content-type,
    content-disposition). Транспортные (content-length, transfer-encoding,
    connection) отбрасываем — они пересчитаются при re-play."""
    KEEP = {"content-type", "content-disposition", "cache-control", "etag"}
    return {k: v for k, v in headers.items() if k.lower() in KEEP}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Ранний opt-out: чужой метод, нет header'а, нет auth.
        if request.method not in _IDEMPOTENT_METHODS:
            return await call_next(request)
        key = request.headers.get(_IDEMPOTENCY_HEADER)
        if not key:
            return await call_next(request)
        # Валидация ключа: 8-128 символов, printable ASCII.
        if not (8 <= len(key) <= 128) or not key.isprintable():
            return await call_next(request)

        user_name = _extract_username(request)
        if not user_name:
            # Без auth нельзя надёжно scope'ить ключ, пропускаем.
            return await call_next(request)

        # Импорты локально: избегаем цикла (database → config → …).
        from database.database import new_session
        from data import idempotency_key as ik_data

        # 1. Lookup существующей записи.
        async with new_session() as session:
            existing = await ik_data.get_idempotency_key(
                session, user_name=user_name, key=key
            )
        if existing is not None:
            headers = existing.response_headers or {}
            headers["x-idempotent-replay"] = "true"
            return Response(
                content=existing.response_body,
                status_code=existing.status_code,
                headers=headers,
            )

        # 2. Не было — выполняем и на 2xx кэшируем.
        response = await call_next(request)
        # Не кэшируем не-2xx (клиент может повторить и попасть в success).
        if not (200 <= response.status_code < 300):
            return response

        # Читаем body полностью (иначе не сможем и сохранить, и отдать).
        body_bytes = await _read_body_bytes(response)
        # Сохраняем в БД — best effort, ошибку логируем но не пробрасываем.
        try:
            async with new_session() as session:
                await ik_data.create_idempotency_key(
                    session,
                    user_name=user_name,
                    key=key,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    response_body=body_bytes,
                    response_headers=_serializable_headers(response.headers),
                    ttl_hours=_IDEMPOTENCY_TTL_HOURS,
                )
        except Exception as e:  # noqa: BLE001
            # Возможно, race с concurrent-запросом (uniq user+key) —
            # ничего страшного: 2-я запись бы просто продублировала кэш.
            logger.warning(f"idempotency-cache save failed: {e!r}")

        # Пересобираем ответ (body_iterator уже exhausted).
        return Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
