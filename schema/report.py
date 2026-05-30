from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List
from datetime import date

# ========== БАЗОВЫЕ СХЕМЫ ==========

class ReportBase(BaseModel):
    """Базовая схема отчета (без user_id для входящих данных)"""
    number: str = Field(..., min_length=1, max_length=50, description="Номер отчета")
    period_id: int = Field(..., ge=1, description="ID периода")
    contract_id: int = Field(..., ge=1, description="ID контракта")
    object_id: int = Field(..., ge=1, description="ID объекта")
    description: Optional[str] = Field(None, max_length=1000, description="Описание отчета")
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ СОЗДАНИЯ ==========

class ReportCreate(BaseModel):
    """Схема для создания отчета (без user_id).

    Номер генерируется сервером по маске
    "{object_id}/{MM}/{YYYY}/{customer.short_name}/{contract.short_subject}"
    из переданного report_period (формат "YYYY-MM").

    period_id / contract_id / object_id опциональны: если не переданы,
    бэк вытащит их из выбранной заявки (order.object.period_id,
    order.contract_id, order.object_id). Если переданы — должны совпадать
    с тем, что лежит на заявке.
    """
    order_id: int = Field(..., ge=1, description="ID заявки (связь 1:1)")
    period_id: Optional[int] = Field(None, ge=1, description="ID периода (опц., возьмётся из заявки)")
    contract_id: Optional[int] = Field(None, ge=1, description="ID контракта (опц., возьмётся из заявки)")
    object_id: Optional[int] = Field(None, ge=1, description="ID объекта (опц., возьмётся из заявки)")
    description: Optional[str] = Field(None, max_length=1000, description="Описание отчета")
    report_period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
                               description="Отчётный период в формате YYYY-MM")

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ ==========

class ReportUpdate(BaseModel):
    """Схема для обновления отчета (все поля опциональны)"""
    number: Optional[str] = Field(None, min_length=1, max_length=50)
    period_id: Optional[int] = Field(None, ge=1)
    contract_id: Optional[int] = Field(None, ge=1)
    object_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000)
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ СМЕНЫ СТАТУСА ==========

class ReportStatusUpdate(BaseModel):
    """Схема для смены статуса отчёта (FK на spec_statuss)."""
    status_id: int = Field(..., ge=1, description="ID статуса из справочника spec_statuss")

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОТВЕТА ==========

class ReportResponse(BaseModel):
    """Полная информация об отчете (с user_id для ответа)"""
    id: int
    number: str
    status_id: int
    period_id: int
    contract_id: int
    object_id: int
    user_id: int  # 👈 user_id только в ответе
    created_at: date
    description: Optional[str] = None

    # Связанные данные
    period_name: Optional[str] = Field(None, description="Название периода")
    contract_number: Optional[str] = Field(None, description="Номер контракта")
    object_name: Optional[str] = Field(None, description="Название объекта")
    user_name: Optional[str] = Field(None, description="Имя пользователя")
    status_name: Optional[str] = Field(None, description="Название статуса")
    status_code: Optional[str] = Field(None, description="Код статуса")
    order_id: Optional[int] = Field(None, description="ID связанной заявки")
    order_number: Optional[str] = Field(None, description="Номер связанной заявки")

    model_config = ConfigDict(from_attributes=True)


# ========== КРАТКАЯ СХЕМА ДЛЯ СПИСКА ==========

class ReportListResponse(BaseModel):
    """Краткая информация об отчете для списков"""
    id: int
    number: str
    status_id: int
    status_name: Optional[str] = None
    status_code: Optional[str] = None
    created_at: date
    period_name: Optional[str] = None
    contract_number: Optional[str] = None
    object_name: Optional[str] = None
    user_name: Optional[str] = None
    order_id: Optional[int] = None
    order_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМА ДЛЯ ВЫПАДАЮЩЕГО СПИСКА ==========

class ReportOptionResponse(BaseModel):
    """Минимальная информация об отчете для выпадающих списков"""
    id: int
    number: str
    status_id: int
    status_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)