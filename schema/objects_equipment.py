from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date

# ========== БАЗОВЫЕ СХЕМЫ ==========

class ObjectsEquipmentBase(BaseModel):
    """Базовая схема связи объекта с оборудованием"""
    object_id: int = Field(..., ge=1, description="ID объекта")
    equipment_id: int = Field(..., ge=1, description="ID оборудования")
    count: int = Field(..., ge=0, description="Количество единиц оборудования на объекте")
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ СОЗДАНИЯ ==========

class ObjectsEquipmentCreate(BaseModel):
    """Схема для создания связи объекта с оборудованием"""
    object_id: int = Field(..., ge=1, description="ID объекта")
    equipment_id: int = Field(..., ge=1, description="ID оборудования")
    count: int = Field(..., ge=1, description="Количество единиц оборудования на объекте (минимум 1)")
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ ==========

class ObjectsEquipmentUpdate(BaseModel):
    """Схема для обновления связи объекта с оборудованием"""
    count: Optional[int] = Field(None, ge=1, description="Новое количество единиц оборудования")
    equipment_id: Optional[int] = Field(None, ge=1, description="ID оборудования (для замены)")
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМА ДЛЯ ОБНОВЛЕНИЯ КОЛИЧЕСТВА ==========

class UpdateEquipmentCount(BaseModel):
    """Схема для обновления только количества оборудования на объекте"""
    count: int = Field(..., ge=1, description="Новое количество единиц оборудования")
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОТВЕТА ==========

class ObjectsEquipmentResponse(ObjectsEquipmentBase):
    """Полная информация о связи объекта с оборудованием"""
    id: int
    
    # Связанные данные
    object_name: Optional[str] = Field(None, description="Название объекта")
    equipment_name: Optional[str] = Field(None, description="Название оборудования")
    equipment_inventory_number: Optional[str] = Field(None, description="Инвентарный номер оборудования")
    equipment_serial_number: Optional[str] = Field(None, description="Серийный номер оборудования")
    
    model_config = ConfigDict(from_attributes=True)


# ========== КРАТКАЯ СХЕМА ДЛЯ СПИСКА ==========

class ObjectsEquipmentListResponse(BaseModel):
    """Краткая информация о связи объекта с оборудованием для списков"""
    id: int
    object_id: int
    equipment_id: int
    count: int
    object_name: Optional[str] = None
    equipment_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМА ДЛЯ ОБОРУДОВАНИЯ НА ОБЪЕКТЕ ==========

class EquipmentOnObjectResponse(BaseModel):
    """Информация об оборудовании на конкретном объекте"""
    id: int  # ID записи в objects_equipments
    equipment_id: int
    equipment_name: str
    inventory_number: str
    serial_number: str
    count: int
    installation_date: Optional[date] = None
    is_active: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМА ДЛЯ ДОБАВЛЕНИЯ ОБОРУДОВАНИЯ НА ОБЪЕКТ ==========

class AddEquipmentToObject(BaseModel):
    """Схема для добавления оборудования на объект"""
    equipment_id: int = Field(..., ge=1, description="ID оборудования")
    count: int = Field(..., ge=1, description="Количество единиц")
    
    model_config = ConfigDict(from_attributes=True)