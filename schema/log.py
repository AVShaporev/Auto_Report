from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    kind: str
    function: Optional[str] = None
    module: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    user: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_sec: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None


class LogFilters(BaseModel):
    """Query-параметры фильтрации логов."""
    kind: Optional[str] = Field(None, description="function | http")
    function: Optional[str] = Field(None, description="Подстрока в имени функции (case-insensitive)")
    user: Optional[str] = Field(None, description="Подстрока в имени пользователя (case-insensitive)")
    module: Optional[str] = Field(None, description="Подстрока в модуле")
    path: Optional[str] = Field(None, description="Подстрока в HTTP-пути")
    method: Optional[str] = Field(None, description="HTTP-метод (GET/POST/PUT/DELETE)")
    status_code: Optional[int] = Field(None, description="HTTP-код ответа")
    duration_min: Optional[float] = Field(None, ge=0, description="Длительность >= (сек)")
    duration_max: Optional[float] = Field(None, ge=0, description="Длительность <= (сек)")
    date_from: Optional[datetime] = Field(None, description="started_at >= (ISO 8601)")
    date_to: Optional[datetime] = Field(None, description="started_at <= (ISO 8601)")
    sort_by: str = Field("started_at", description="started_at | duration_sec | function | user")
    sort_order: str = Field("desc", description="asc | desc")
