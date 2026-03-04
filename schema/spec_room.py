from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема типа помещения
class SpecRoomBase(BaseModel):
    """Базовая схема типа помещения"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа помещения")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа помещения
class SpecRoomCreate(SpecRoomBase):
    """Схема для создания типа помещения"""
    pass

# Схема для обновления типа помещения (все поля опциональны)
class SpecRoomUpdate(BaseModel):
    """Схема для обновления типа помещения"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecRoomResponse(SpecRoomBase):
    """Полная информация о типе помещения"""
    id: int
    organizations_count: Optional[int] = Field(0, description="Количество организаций с этим типом помещения")
    objects_count: Optional[int] = Field(0, description="Количество объектов с этим типом помещения")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecRoomListResponse(BaseModel):
    """Краткая информация о типе помещения для списков"""
    id: int
    name: str
    organizations_count: int = 0
    objects_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecRoomOptionResponse(BaseModel):
    """Минимальная информация о типе помещения для выпадающих списков"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)