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
    object_id: Optional[int] = None
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
    # v1.0.10 — фильтры в ObjectsListView mobile (регион/район/нас.пункт).
    region_name: Optional[str] = None
    arial_name: Optional[str] = None
    locality_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MobileReportListItem(BaseModel):
    id: int
    number: str
    object_id: Optional[int] = None
    object_name: Optional[str] = None
    status_name: Optional[str] = None
    created_at: date
    author_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MobileOrderListItem(BaseModel):
    """Плановая/аварийная заявка на ТО — то, с чем инженер работает на объекте."""
    id: int
    number: str
    status_id: int
    status_name: Optional[str] = None  # ру-имя из spec_order_statuses
    order_type: Optional[str] = None
    object_id: Optional[int] = None
    object_name: Optional[str] = None
    period_start_date: Optional[date] = None
    created_at: Optional[datetime] = None
    assigned_to_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MobileObjectEquipmentItem(BaseModel):
    """Единица оборудования на объекте (drill-down из ObjectDetailView)."""
    object_equipment_id: int
    equipment_id: int
    equipment_name: str
    count: int
    inventory_number: Optional[str] = None
    serial_number: Optional[str] = None
    open_issues_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class MobileObjectEquipmentDetail(BaseModel):
    """Деталь одной единицы оборудования (drill-down mobile — v1.0.9).

    Отдельная от MobileObjectEquipmentItem: добавлены equipment_type_name,
    system_name, installation_date, object_id/object_name. Инженерский
    endpoint без RBAC (`object_equipment_read` часто отсутствует у роли
    инженера, а деталь на mobile нужна).
    """
    object_equipment_id: int
    equipment_id: int
    equipment_name: str
    equipment_type_name: Optional[str] = None
    system_name: Optional[str] = None
    count: int
    inventory_number: Optional[str] = None
    serial_number: Optional[str] = None
    installation_date: Optional[str] = None
    object_id: int
    object_name: Optional[str] = None
    open_issues_count: int = 0

    model_config = ConfigDict(from_attributes=True)
