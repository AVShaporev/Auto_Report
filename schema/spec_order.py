from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal

# SLA-режим типа заявки (см. Spec_Order.sla_kind, миграция f5c6d7e8f9a0)
SlaKind = Literal['periodic', 'from_creation', 'manual']

# Базовая схема типа заявки
class SpecOrderBase(BaseModel):
    """Базовая схема типа заявки"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа заявки")
    short_name: Optional[str] = Field(None, max_length=50, description="Краткое наименование")
    code: Optional[str] = Field(None, min_length=2, max_length=50, description="Машинный код (emergency, primary, planned, test, ...)")

    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа заявки
class SpecOrderCreate(SpecOrderBase):
    """Схема для создания типа заявки"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")
    is_default_planned: bool = Field(False, description="Использовать для авто-генерации плановых заявок (макс. один TRUE на справочник)")
    is_default_primary: bool = Field(False, description="Использовать для авто-генерации заявок первичного обследования (макс. один TRUE на справочник)")
    sla_kind: SlaKind = Field('manual', description="Как считать due_date: periodic / from_creation / manual")
    sla_days: Optional[int] = Field(None, ge=1, le=365, description="Дней на исполнение (обязателен для from_creation)")
    sla_days_workdays: bool = Field(False, description="sla_days в рабочих днях (сб/вс пропускаются) — только для from_creation")

# Схема для обновления типа заявки (все поля опциональны)
class SpecOrderUpdate(BaseModel):
    """Схема для обновления типа заявки"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    short_name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    is_default_planned: Optional[bool] = Field(None, description="Сделать видом по умолчанию для плановых авто-заявок")
    is_default_primary: Optional[bool] = Field(None, description="Сделать видом по умолчанию для авто-заявок первичного обследования")
    sla_kind: Optional[SlaKind] = Field(None)
    sla_days: Optional[int] = Field(None, ge=1, le=365)
    sla_days_workdays: Optional[bool] = Field(None)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecOrderResponse(SpecOrderBase):
    """Полная информация о типе заявки"""
    id: int
    is_system: bool = False
    is_default_planned: bool = False
    is_default_primary: bool = False
    description: Optional[str] = None
    orders_count: Optional[int] = Field(0, description="Количество заявок этого типа")
    template_filename: Optional[str] = Field(None, description="Оригинальное имя файла шаблона документа (если привязан)")
    sla_kind: SlaKind = 'manual'
    sla_days: Optional[int] = None
    sla_days_workdays: bool = False

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecOrderListResponse(BaseModel):
    """Краткая информация о типе заявки для списков"""
    id: int
    is_system: bool = False
    is_default_planned: bool = False
    is_default_primary: bool = False
    name: str
    short_name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    orders_count: int = 0
    template_filename: Optional[str] = None
    sla_kind: SlaKind = 'manual'
    sla_days: Optional[int] = None
    sla_days_workdays: bool = False

    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecOrderOptionResponse(BaseModel):
    """Минимальная информация о типе заявки для выпадающих списков"""
    id: int
    name: str
    short_name: Optional[str] = None
    code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)