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
    """Схема для создания отчета (без user_id)"""
    number: str = Field(..., min_length=1, max_length=50, description="Номер отчета")
    period_id: int = Field(..., ge=1, description="ID периода")
    contract_id: int = Field(..., ge=1, description="ID контракта")
    object_id: int = Field(..., ge=1, description="ID объекта")
    description: Optional[str] = Field(None, max_length=1000, description="Описание отчета")
    
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


# ========== СХЕМЫ ДЛЯ УТВЕРЖДЕНИЯ ==========

class ReportApprove(BaseModel):
    """Схема для утверждения отчета"""
    check_pass: bool = Field(True, description="Утвердить отчет")
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОТВЕТА ==========

class ReportResponse(BaseModel):
    """Полная информация об отчете (с user_id для ответа)"""
    id: int
    number: str
    check_pass: bool
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
    order_number: Optional[str] = Field(None, description="Номер заявки")
    
    model_config = ConfigDict(from_attributes=True)


# ========== КРАТКАЯ СХЕМА ДЛЯ СПИСКА ==========

class ReportListResponse(BaseModel):
    """Краткая информация об отчете для списков"""
    id: int
    number: str
    check_pass: bool
    created_at: date
    period_name: Optional[str] = None
    contract_number: Optional[str] = None
    object_name: Optional[str] = None
    user_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМА ДЛЯ ВЫПАДАЮЩЕГО СПИСКА ==========

class ReportOptionResponse(BaseModel):
    """Минимальная информация об отчете для выпадающих списков"""
    id: int
    number: str
    check_pass: bool
    
    model_config = ConfigDict(from_attributes=True)