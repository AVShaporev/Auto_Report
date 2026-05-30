from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime


# ========== БАЗОВЫЕ СХЕМЫ ==========

class IssueBase(BaseModel):
    """Базовая схема неисправности"""
    number: str = Field(..., min_length=1, max_length=50, description="Номер неисправности")
    title: str = Field(..., min_length=3, max_length=200, description="Краткое описание")
    description: Optional[str] = Field(None, max_length=5000, description="Подробное описание")
    priority_id: int = Field(..., ge=1, description="ID приоритета из справочника spec_prioritys")
    detected_date: date = Field(..., description="Дата обнаружения")
    is_critical: bool = Field(False, description="Критическая неисправность")

    # Связи
    object_equipment_id: int = Field(..., ge=1, description="ID связи объекта с оборудованием")
    assigned_to_id: Optional[int] = Field(None, ge=1, description="ID ответственного пользователя")

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ СОЗДАНИЯ ==========

class IssueCreate(BaseModel):
    """Схема для создания неисправности.

    Номер генерируется сервером (как у отчётов/заявок). Приоритет — FK на spec_prioritys.
    """
    title: str = Field(..., min_length=3, max_length=200, description="Краткое описание")
    description: Optional[str] = Field(None, max_length=5000, description="Подробное описание")
    priority_id: int = Field(..., ge=1, description="ID приоритета из справочника spec_prioritys")
    detected_date: date = Field(..., description="Дата обнаружения")
    is_critical: bool = Field(False, description="Критическая неисправность")
    object_equipment_id: int = Field(..., ge=1, description="ID связи объекта с оборудованием")
    assigned_to_id: Optional[int] = Field(None, ge=1, description="ID ответственного пользователя")

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ ==========

class IssueUpdate(BaseModel):
    """Схема для обновления неисправности (все поля опциональны)"""
    number: Optional[str] = Field(None, min_length=1, max_length=50)
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    priority_id: Optional[int] = Field(None, ge=1)
    detected_date: Optional[date] = None
    is_critical: Optional[bool] = None
    object_equipment_id: Optional[int] = Field(None, ge=1)
    assigned_to_id: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ СТАТУСА ==========

class IssueStatusUpdate(BaseModel):
    """Схема для обновления статуса неисправности"""
    status_id: int = Field(..., ge=1, description="ID нового статуса из справочника spec_statuss")
    resolved_date: Optional[date] = Field(None, description="Дата устранения (обязательна, если статус имеет код 'resolved')")

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОТВЕТА ==========

class IssueResponse(IssueBase):
    """Полная информация о неисправности"""
    id: int
    status_id: int = Field(..., description="ID статуса из справочника")
    status_name: Optional[str] = Field(None, description="Наименование статуса")
    status_code: Optional[str] = Field(None, description="Код статуса (new, in_progress, resolved, closed)")
    priority_name: Optional[str] = Field(None, description="Наименование приоритета")
    priority_code: Optional[str] = Field(None, description="Машинный код приоритета (low, medium, high, critical)")
    resolved_date: Optional[date] = None
    is_resolved: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    reported_by_id: int

    # Связанные данные
    object_id: Optional[int] = Field(None, description="ID объекта (через object_equipment)")
    object_name: Optional[str] = Field(None, description="Название объекта")
    equipment_id: Optional[int] = Field(None, description="ID оборудования (через object_equipment)")
    equipment_name: Optional[str] = Field(None, description="Название оборудования")
    equipment_inventory_number: Optional[str] = Field(None, description="Инвентарный номер оборудования")
    reported_by_name: Optional[str] = Field(None, description="Имя пользователя, сообщившего о неисправности")
    assigned_to_name: Optional[str] = Field(None, description="Имя ответственного пользователя")

    model_config = ConfigDict(from_attributes=True)


# ========== КРАТКАЯ СХЕМА ДЛЯ СПИСКА ==========

class IssueListResponse(BaseModel):
    """Краткая информация о неисправности для списков"""
    id: int
    number: str
    title: str
    status_id: int
    status_name: Optional[str] = None
    status_code: Optional[str] = None
    priority_id: int
    priority_name: Optional[str] = None
    priority_code: Optional[str] = None
    detected_date: date
    resolved_date: Optional[date] = None
    is_resolved: bool
    is_critical: bool
    created_at: datetime

    # Связанные данные
    object_id: Optional[int] = None
    object_name: Optional[str] = None
    equipment_id: Optional[int] = None
    equipment_name: Optional[str] = None
    reported_by_name: Optional[str] = None
    assigned_to_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМА ДЛЯ ВЫПАДАЮЩЕГО СПИСКА ==========

class IssueOptionResponse(BaseModel):
    """Минимальная информация о неисправности для выпадающих списков"""
    id: int
    number: str
    title: str
    status_id: int
    status_code: Optional[str] = None
    status_name: Optional[str] = None
    priority_id: int
    priority_code: Optional[str] = None
    priority_name: Optional[str] = None
    detected_date: date
    is_resolved: bool

    model_config = ConfigDict(from_attributes=True)
