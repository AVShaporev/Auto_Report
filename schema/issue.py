from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List
from datetime import date, datetime

# ========== БАЗОВЫЕ СХЕМЫ ==========

class IssueBase(BaseModel):
    """Базовая схема неисправности"""
    number: str = Field(..., min_length=1, max_length=50, description="Номер неисправности")
    title: str = Field(..., min_length=3, max_length=200, description="Краткое описание")
    description: Optional[str] = Field(None, max_length=5000, description="Подробное описание")
    status: str = Field("new", description="Статус: new, in_progress, resolved, closed")
    priority: str = Field("medium", description="Приоритет: low, medium, high, critical")
    detected_date: date = Field(..., description="Дата обнаружения")
    is_critical: bool = Field(False, description="Критическая неисправность")
    
    # Связи
    object_equipment_id: int = Field(..., ge=1, description="ID связи объекта с оборудованием")
    assigned_to_id: Optional[int] = Field(None, ge=1, description="ID ответственного пользователя")
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ СОЗДАНИЯ ==========

class IssueCreate(BaseModel):
    """Схема для создания неисправности"""
    number: str = Field(..., min_length=1, max_length=50, description="Номер неисправности")
    title: str = Field(..., min_length=3, max_length=200, description="Краткое описание")
    description: Optional[str] = Field(None, max_length=5000, description="Подробное описание")
    priority: str = Field("medium", description="Приоритет: low, medium, high, critical")
    detected_date: date = Field(..., description="Дата обнаружения")
    is_critical: bool = Field(False, description="Критическая неисправность")
    object_equipment_id: int = Field(..., ge=1, description="ID связи объекта с оборудованием")
    assigned_to_id: Optional[int] = Field(None, ge=1, description="ID ответственного пользователя")
    
    @validator('priority')
    def validate_priority(cls, v):
        allowed = ['low', 'medium', 'high', 'critical']
        if v not in allowed:
            raise ValueError(f'Приоритет должен быть одним из: {", ".join(allowed)}')
        return v
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ ==========

class IssueUpdate(BaseModel):
    """Схема для обновления неисправности (все поля опциональны)"""
    number: Optional[str] = Field(None, min_length=1, max_length=50)
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    priority: Optional[str] = Field(None)
    detected_date: Optional[date] = None
    is_critical: Optional[bool] = None
    object_equipment_id: Optional[int] = Field(None, ge=1)
    assigned_to_id: Optional[int] = Field(None, ge=1)
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None:
            allowed = ['low', 'medium', 'high', 'critical']
            if v not in allowed:
                raise ValueError(f'Приоритет должен быть одним из: {", ".join(allowed)}')
        return v
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ СТАТУСА ==========

class IssueStatusUpdate(BaseModel):
    """Схема для обновления статуса неисправности"""
    status: str = Field(..., description="Новый статус: new, in_progress, resolved, closed")
    resolved_date: Optional[date] = Field(None, description="Дата устранения (обязательно при статусе resolved)")
    
    @validator('status')
    def validate_status(cls, v):
        allowed = ['new', 'in_progress', 'resolved', 'closed']
        if v not in allowed:
            raise ValueError(f'Статус должен быть одним из: {", ".join(allowed)}')
        return v
    
    @validator('resolved_date')
    def validate_resolved_date(cls, v, values):
        if 'status' in values and values['status'] == 'resolved' and v is None:
            raise ValueError('Дата устранения обязательна при статусе "resolved"')
        return v
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОТВЕТА ==========

class IssueResponse(IssueBase):
    """Полная информация о неисправности"""
    id: int
    resolved_date: Optional[date] = None
    is_resolved: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    reported_by_id: int
    
    # Связанные данные
    object_name: Optional[str] = Field(None, description="Название объекта")
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
    status: str
    priority: str
    detected_date: date
    resolved_date: Optional[date] = None
    is_resolved: bool
    is_critical: bool
    created_at: datetime
    
    # Связанные данные
    object_name: Optional[str] = None
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
    status: str
    priority: str
    detected_date: date
    is_resolved: bool
    
    model_config = ConfigDict(from_attributes=True)