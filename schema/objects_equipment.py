from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date

# ========== БАЗОВЫЕ СХЕМЫ ==========

class ObjectsEquipmentBase(BaseModel):
    """Базовая схема связи объекта с оборудованием"""
    object_id: int = Field(..., ge=1, description="ID объекта")
    equipment_id: int = Field(..., ge=1, description="ID оборудования")
    count: int = Field(..., ge=0, description="Количество единиц оборудования на объекте")
    inventory_number: Optional[str] = Field(None, max_length=50, description="Инвентарный номер экземпляра на объекте")
    serial_number: Optional[str] = Field(None, max_length=50, description="Серийный номер экземпляра на объекте")
    installation_date: Optional[date] = Field(None, description="Дата установки/ввода в эксплуатацию")
    spec_system_id: Optional[int] = Field(None, ge=1, description="ID типа обслуживаемой системы (опционально)")

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ СОЗДАНИЯ ==========

class ObjectsEquipmentCreate(BaseModel):
    """Схема для создания связи объекта с оборудованием"""
    object_id: int = Field(..., ge=1, description="ID объекта")
    equipment_id: int = Field(..., ge=1, description="ID оборудования")
    count: int = Field(..., ge=1, description="Количество единиц оборудования на объекте (минимум 1)")
    inventory_number: Optional[str] = Field(None, max_length=50)
    serial_number: Optional[str] = Field(None, max_length=50)
    installation_date: Optional[date] = None
    spec_system_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ ==========

class ObjectsEquipmentUpdate(BaseModel):
    """Схема для обновления связи объекта с оборудованием"""
    count: Optional[int] = Field(None, ge=1, description="Новое количество единиц оборудования")
    equipment_id: Optional[int] = Field(None, ge=1, description="ID оборудования (для замены)")
    inventory_number: Optional[str] = Field(None, max_length=50)
    serial_number: Optional[str] = Field(None, max_length=50)
    installation_date: Optional[date] = None
    spec_system_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000)

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
    description: Optional[str] = None

    # Связанные данные
    object_name: Optional[str] = Field(None, description="Название объекта")
    equipment_name: Optional[str] = Field(None, description="Название оборудования")

    model_config = ConfigDict(from_attributes=True)


# ========== КРАТКАЯ СХЕМА ДЛЯ СПИСКА ==========

class ObjectsEquipmentListResponse(BaseModel):
    """Краткая информация о связи объекта с оборудованием для списков"""
    id: int
    object_id: int
    equipment_id: int
    count: int
    inventory_number: Optional[str] = None
    serial_number: Optional[str] = None
    installation_date: Optional[date] = None
    object_name: Optional[str] = None
    equipment_name: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМА ДЛЯ ОБОРУДОВАНИЯ НА ОБЪЕКТЕ ==========

class EquipmentOnObjectResponse(BaseModel):
    """Информация об оборудовании на конкретном объекте"""
    id: int  # ID записи в objects_equipments
    equipment_id: int
    equipment_name: str
    count: int
    inventory_number: Optional[str] = None
    serial_number: Optional[str] = None
    installation_date: Optional[date] = None
    is_active: Optional[bool] = None
    spec_system_id: Optional[int] = None
    spec_system_name: Optional[str] = None
    spec_system_short_name: Optional[str] = None
    spec_system_is_fire_protection: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМА ДЛЯ ДОБАВЛЕНИЯ ОБОРУДОВАНИЯ НА ОБЪЕКТ ==========

class AddEquipmentToObject(BaseModel):
    """Схема для добавления оборудования на объект"""
    equipment_id: int = Field(..., ge=1, description="ID оборудования")
    count: int = Field(..., ge=1, description="Количество единиц")
    inventory_number: Optional[str] = Field(None, max_length=50)
    serial_number: Optional[str] = Field(None, max_length=50)
    installation_date: Optional[date] = None
    spec_system_id: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(from_attributes=True)
