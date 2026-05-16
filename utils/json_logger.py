"""
JSON-лог с понедельной ротацией: logs_{DD.MM.YYYY}-{DD.MM.YYYY}.json (JSONL).

- `current_user_var` — ContextVar, ставится в middleware из Bearer-токена и читается
  декоратором @timer, чтобы записать имя пользователя без явных аргументов.
- `extract_payload` — для CRUD-функций (create_*, update_*, delete_*, add_*, approve_*, set_*)
  возвращает sanitized dict с переданным payload (Pydantic-схема или updates-dict).
  Для select-функций (get_*/count_*/check_*) возвращает None.
- Sensitive-поля (password, hash, token и т.п.) маскируются.
- Имя файла рассчитывается по timestamp КАЖДОЙ записи — ротация автоматическая в Пн 00:00.
"""

import json
import threading
from contextvars import ContextVar
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Optional


current_user_var: ContextVar[Optional[str]] = ContextVar("current_user", default=None)

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_SENSITIVE_KEYS = {
    "password", "hash", "secret",
    "token", "access_token", "refresh_token",
    "new_password", "old_password",
}
_MASK = "***"

_CRUD_PREFIXES = ("create_", "update_", "delete_", "add_", "approve_", "set_")


def mask_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (_MASK if (isinstance(k, str) and k.lower() in _SENSITIVE_KEYS) else mask_payload(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [mask_payload(v) for v in value]
    if isinstance(value, tuple):
        return [mask_payload(v) for v in value]
    return value


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    return str(value)


def extract_payload(func_name: str, args: tuple, kwargs: dict) -> Optional[dict]:
    if not func_name.startswith(_CRUD_PREFIXES):
        return None

    candidates = list(args) + list(kwargs.values())
    for v in candidates:
        if hasattr(v, "model_dump") and callable(v.model_dump):
            try:
                return mask_payload(_to_jsonable(v.model_dump()))
            except Exception:
                continue
        if hasattr(v, "dict") and callable(getattr(v, "dict")) and not isinstance(v, dict):
            try:
                return mask_payload(_to_jsonable(v.dict()))
            except Exception:
                continue
        if isinstance(v, dict):
            return mask_payload(_to_jsonable(v))
    return None


def _week_filename(ts: datetime) -> str:
    monday = (ts - timedelta(days=ts.weekday())).date()
    sunday = monday + timedelta(days=6)
    return f"logs_{monday.strftime('%d.%m.%Y')}-{sunday.strftime('%d.%m.%Y')}.json"


class _JsonWeekLogger:
    def __init__(self, log_dir: Path):
        self._dir = log_dir
        self._lock = threading.Lock()

    def write(self, event: dict) -> None:
        ts_iso = event.get("ended_at") or event.get("started_at")
        try:
            ts = datetime.fromisoformat(ts_iso) if ts_iso else datetime.now()
        except Exception:
            ts = datetime.now()
        path = self._dir / _week_filename(ts)
        line = json.dumps(event, ensure_ascii=False)
        with self._lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")


json_logger = _JsonWeekLogger(LOG_DIR)
