from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date

# ========== БАЗОВАЯ СХЕМА ==========

class EquipmentBase(BaseModel):
    """Базовая схема оборудования (упрощенная)"""
    name: str = Field(..., min_length=2, max_length=200, description="Наименование оборудования")
    inventory_number: str = Field(..., min_length=1, max_length=50, description="Инвентарный номер")
    serial_number: str = Field(..., min_length=1, max_length=50, description="Серийный номер")
    installation_date: date = Field(..., description="Дата установки")
    is_active: bool = Field(True, description="Активно/списано")
    spec_equipment_id: int = Field(..., ge=1, description="ID типа оборудования")
    
    model_config = ConfigDict(from_attributes=True)

# ========== СХЕМА ДЛЯ СОЗДАНИЯ ==========

class EquipmentCreate(BaseModel):
    """Схема для создания оборудования"""
    name: str = Field(..., min_length=2, max_length=200, description="Наименование оборудования")
    inventory_number: str = Field(..., min_length=1, max_length=50, description="Инвентарный номер")
    serial_number: str = Field(..., min_length=1, max_length=50, description="Серийный номер")
    installation_date: date = Field(..., description="Дата установки")
    is_active: bool = Field(True, description="Активно/списано")
    spec_equipment_id: int = Field(..., ge=1, description="ID типа оборудования")
    
    model_config = ConfigDict(from_attributes=True)

# ========== СХЕМА ДЛЯ ОБНОВЛЕНИЯ ==========

class EquipmentUpdate(BaseModel):
    """Схема для обновления оборудования (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    inventory_number: Optional[str] = Field(None, min_length=1, max_length=50)
    serial_number: Optional[str] = Field(None, min_length=1, max_length=50)
    installation_date: Optional[date] = None
    is_active: Optional[bool] = None
    spec_equipment_id: Optional[int] = Field(None, ge=1)
    
    model_config = ConfigDict(from_attributes=True)

# ========== СХЕМА ДЛЯ ОТВЕТА ==========

class EquipmentResponse(EquipmentBase):
    """Полная информация об оборудовании"""
    id: int
    spec_equipment_name: Optional[str] = Field(None, description="Название типа оборудования")
    
    model_config = ConfigDict(from_attributes=True)

# ========== КРАТКАЯ СХЕМА ДЛЯ СПИСКА ==========

class EquipmentListResponse(BaseModel):
    """Краткая информация об оборудовании для списков"""
    id: int
    name: str
    inventory_number: str
    serial_number: str
    installation_date: date
    is_active: bool
    spec_equipment_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# ========== СХЕМА ДЛЯ ВЫПАДАЮЩЕГО СПИСКА ==========

class EquipmentOptionResponse(BaseModel):
    """Минимальная информация об оборудовании для выпадающих списков"""
    id: int
    name: str
    inventory_number: str
    serial_number: str
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)