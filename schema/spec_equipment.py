from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема типа оборудования
class SpecEquipmentBase(BaseModel):
    """Базовая схема типа оборудования"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа оборудования")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа оборудования
class SpecEquipmentCreate(SpecEquipmentBase):
    """Схема для создания типа оборудования"""
    pass

# Схема для обновления типа оборудования (все поля опциональны)
class SpecEquipmentUpdate(BaseModel):
    """Схема для обновления типа оборудования"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecEquipmentResponse(SpecEquipmentBase):
    """Полная информация о типе оборудования"""
    id: int
    equipments_count: Optional[int] = Field(0, description="Количество оборудования этого типа")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecEquipmentListResponse(BaseModel):
    """Краткая информация о типе оборудования для списков"""
    id: int
    name: str
    equipments_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecEquipmentOptionResponse(BaseModel):
    """Минимальная информация о типе оборудования для выпадающих списков"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)