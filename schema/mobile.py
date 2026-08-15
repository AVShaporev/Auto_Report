"""Compact Pydantic-схемы для mobile-клиента (Mobile M1.3).

Мобилка (PWA + Capacitor) на flaky-сети живёт в поле — нужны маленькие
JSON-payload'ы без heavy relations. Здесь только те поля, которые
реально показываются на mobile-экране list-view. Клиент, кликая на
элемент, догружает подробности через существующие эндпоинты
(/api/issues/{id}, /api/objects/{id}, /api/reports/{id}).

Ориентир по размеру: одна запись ≤300 байт JSON (в среднем ~150-200).
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MobileIssueListItem(BaseModel):
    id: int
    number: str
    title: str
    status_name: Optional[str] = None
    priority_code: Optional[str] = None
    is_critical: bool = False
    is_resolved: bool = False
    detected_date: date
    resolved_date: Optional[date] = None
    object_name: Optional[str] = None
    equipment_name: Optional[str] = None
    assigned_to_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MobileObjectSummaryItem(BaseModel):
    id: int
    name: str
    address_short: Optional[str] = None
    contract_number: Optional[str] = None
    build_number: Optional[str] = None
    room_number: Optional[str] = None
    number_in_contract: int
    equipment_count: int = 0
    open_issues_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class MobileReportListItem(BaseModel):
    id: int
    number: str
    object_name: Optional[str] = None
    status_name: Optional[str] = None
    created_at: date
    author_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MobileOrderListItem(BaseModel):
    """Плановая/аварийная заявка на ТО — то, с чем инженер работает на объекте."""
    id: int
    number: str
    status: Optional[str] = None       # системный код: new/in_progress/completed/cancelled
    status_name: Optional[str] = None  # ру-имя из spec_order_statuses (может быть None если справочник рассинхронизирован)
    order_type: Optional[str] = None
    object_name: Optional[str] = None
    period_start_date: Optional[date] = None
    created_at: Optional[datetime] = None
    assigned_to_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
