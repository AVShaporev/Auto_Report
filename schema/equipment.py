from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# ========== БАЗОВАЯ СХЕМА ==========

class EquipmentBase(BaseModel):
    """Базовая схема справочника оборудования"""
    name: str = Field(..., min_length=2, max_length=200, description="Наименование оборудования")
    is_active: bool = Field(True, description="Активно/списано")
    spec_equipment_id: int = Field(..., ge=1, description="ID типа оборудования")

    model_config = ConfigDict(from_attributes=True)

# ========== СХЕМА ДЛЯ СОЗДАНИЯ ==========

class EquipmentCreate(BaseModel):
    """Схема для создания справочной позиции оборудования"""
    name: str = Field(..., min_length=2, max_length=200, description="Наименование оборудования")
    is_active: bool = Field(True, description="Активно/списано")
    spec_equipment_id: int = Field(..., ge=1, description="ID типа оборудования")

    model_config = ConfigDict(from_attributes=True)

# ========== СХЕМА ДЛЯ ОБНОВЛЕНИЯ ==========

class EquipmentUpdate(BaseModel):
    """Схема для обновления оборудования (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
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
    is_active: bool
    spec_equipment_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ========== СХЕМА ДЛЯ ВЫПАДАЮЩЕГО СПИСКА ==========

class EquipmentOptionResponse(BaseModel):
    """Минимальная информация об оборудовании для выпадающих списков"""
    id: int
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
