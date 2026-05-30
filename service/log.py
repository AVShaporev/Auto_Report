"""Чтение JSON-логов из logs/logs_<DD.MM.YYYY>-<DD.MM.YYYY>.json (JSONL).

Фильтрация и пагинация — в памяти. Текущие объёмы (~тысячи записей в неделю)
позволяют это без индексов; если файлы вырастут — переносить в БД."""

import json
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Tuple, Optional

from fastapi import HTTPException, status

from model.user import User
from schema.log import LogEntry, LogFilters
from schema.pagination import PaginationParams


LOG_DIR = Path("logs")
_FILENAME_RE = re.compile(r"^logs_(\d{2}\.\d{2}\.\d{4})-(\d{2}\.\d{2}\.\d{4})\.json$")


def _check_admin(current_user: User) -> None:
    role = current_user.role
    if not (getattr(role, "is_admin", False) or getattr(role, "is_superadmin", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Просмотр логов доступен только администраторам",
        )


def _to_local_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Приводит datetime к naive-локальному.

    Логи на диске пишутся как naive-local (`datetime.now().isoformat()` без TZ),
    поэтому фильтрующая граница тоже должна быть naive-local. Если клиент
    прислал aware-значение (например, UTC `...Z`), переводим в локальную зону
    и срезаем tzinfo, иначе comparison с naive timestamp из файла кинет TypeError.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def _parse_week_range(name: str) -> Optional[Tuple[date, date]]:
    m = _FILENAME_RE.match(name)
    if not m:
        return None
    try:
        a = datetime.strptime(m.group(1), "%d.%m.%Y").date()
        b = datetime.strptime(m.group(2), "%d.%m.%Y").date()
        return (a, b)
    except ValueError:
        return None


def _relevant_files(date_from: Optional[datetime], date_to: Optional[datetime]) -> List[Path]:
    """Возвращает только файлы тех недель, что пересекаются с date_from/date_to.
    Если границы не заданы — берёт все файлы."""
    if not LOG_DIR.exists():
        return []

    files: List[Tuple[date, Path]] = []
    df = date_from.date() if date_from else None
    dt = date_to.date() if date_to else None

    for p in LOG_DIR.iterdir():
        if not p.is_file():
            continue
        rng = _parse_week_range(p.name)
        if not rng:
            continue
        week_from, week_to = rng
        if df and week_to < df:
            continue
        if dt and week_from > dt:
            continue
        files.append((week_from, p))

    files.sort(key=lambda x: x[0])
    return [p for _, p in files]


def _matches(entry: dict, f: LogFilters) -> bool:
    if f.kind and entry.get("kind") != f.kind:
        return False
    if f.function:
        fn = entry.get("function") or ""
        if f.function.lower() not in fn.lower():
            return False
    if f.user is not None and f.user != "":
        u = entry.get("user") or ""
        if f.user.lower() not in u.lower():
            return False
    if f.module:
        m = entry.get("module") or ""
        if f.module.lower() not in m.lower():
            return False
    if f.path:
        p = entry.get("path") or ""
        if f.path.lower() not in p.lower():
            return False
    if f.method:
        m = entry.get("method") or ""
        if m.upper() != f.method.upper():
            return False
    if f.status_code is not None and entry.get("status_code") != f.status_code:
        return False
    dur = entry.get("duration_sec")
    if f.duration_min is not None and (dur is None or dur < f.duration_min):
        return False
    if f.duration_max is not None and (dur is None or dur > f.duration_max):
        return False
    if f.date_from or f.date_to:
        started = entry.get("started_at")
        if not started:
            return False
        try:
            ts = datetime.fromisoformat(started)
        except ValueError:
            return False
        if f.date_from and ts < f.date_from:
            return False
        if f.date_to and ts > f.date_to:
            return False
    return True


_SORT_KEYS = {"started_at", "ended_at", "duration_sec", "function", "user", "kind"}


def _sort_key(entry: dict, key: str):
    v = entry.get(key)
    if v is None:
        # сортируем None в самый конец при desc и в начало при asc — даём пустую строку/0
        return ("" if key in ("function", "user", "kind") else 0)
    return v


async def list_logs(
    pagination: PaginationParams,
    filters: LogFilters,
    current_user: User,
) -> Tuple[List[LogEntry], int]:
    _check_admin(current_user)

    df_naive = _to_local_naive(filters.date_from)
    dt_naive = _to_local_naive(filters.date_to)
    if df_naive is not filters.date_from or dt_naive is not filters.date_to:
        filters = filters.model_copy(update={"date_from": df_naive, "date_to": dt_naive})

    sort_key = filters.sort_by if filters.sort_by in _SORT_KEYS else "started_at"
    reverse = (filters.sort_order or "desc").lower() != "asc"

    files = _relevant_files(filters.date_from, filters.date_to)

    matched: List[dict] = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        entry = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if _matches(entry, filters):
                        matched.append(entry)
        except OSError:
            continue

    matched.sort(key=lambda e: _sort_key(e, sort_key), reverse=reverse)

    total = len(matched)
    page_slice = matched[pagination.skip : pagination.skip + pagination.limit]
    return [LogEntry(**e) for e in page_slice], total
