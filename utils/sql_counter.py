"""Подсчёт SQL-запросов на каждый HTTP-запрос — диагностика N+1.

Регистрирует event-listener на async engine и считает per-request:
  - сколько SELECT/INSERT/UPDATE/DELETE улетело в БД
  - сколько суммарно времени потрачено внутри драйвера asyncpg
  - top-5 самых частых нормализованных запросов

Данные хранятся в ContextVar — каждый HTTP-запрос имеет свой контекст.
Middleware (`middleware.LogRequestsMiddleware`) делает reset() в начале и
snapshot() в конце, выводя итог в логи и в JSON-лог.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from contextvars import ContextVar
from typing import Optional, TypedDict


class _Snapshot(TypedDict):
    count: int
    total_time_sec: float
    queries: Counter  # normalized SQL → count


def _new_state() -> _Snapshot:
    return {"count": 0, "total_time_sec": 0.0, "queries": Counter()}


# ContextVar держит per-request состояние. None — счётчик отключён (вне middleware).
_state_var: ContextVar[Optional[_Snapshot]] = ContextVar("sql_counter_state", default=None)


def reset() -> None:
    """Включить счётчик для текущего HTTP-запроса (вызывать на старте middleware)."""
    _state_var.set(_new_state())


def snapshot() -> Optional[_Snapshot]:
    """Получить состояние счётчика для текущего запроса. None если не reset()'нут."""
    return _state_var.get()


# Нормализация SQL: схлопываем многострочное форматирование, режем длинные IN-листы,
# чтобы одинаковые по смыслу запросы группировались в Counter.
_WS_RE = re.compile(r"\s+")
_IN_RE = re.compile(r"\bIN\s*\([^)]+\)", re.IGNORECASE)


def _normalize(sql: str) -> str:
    s = _WS_RE.sub(" ", sql).strip()
    s = _IN_RE.sub("IN (...)", s)
    return s[:200]  # обрезаем для лога


def _before(conn, cursor, statement, parameters, context, executemany):
    context._sql_start = time.perf_counter()


def _after(conn, cursor, statement, parameters, context, executemany):
    state = _state_var.get()
    if state is None:
        return
    start = getattr(context, "_sql_start", None)
    if start is None:
        return
    dt = time.perf_counter() - start
    state["count"] += 1
    state["total_time_sec"] += dt
    state["queries"][_normalize(statement)] += 1


def install(engine) -> None:
    """Прицепить listener'ы к движку. Идемпотентно: повторный install не даст дублей."""
    from sqlalchemy import event

    # event.listen работает на sync_engine у AsyncEngine
    target = getattr(engine, "sync_engine", engine)

    # Защита от повторной регистрации (на случай reload)
    if getattr(target, "_sql_counter_installed", False):
        return
    event.listen(target, "before_cursor_execute", _before)
    event.listen(target, "after_cursor_execute", _after)
    target._sql_counter_installed = True
