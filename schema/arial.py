from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема района
class ArialBase(BaseModel):
    """Базовая схема района"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование района")
    spec_arial_id: int = Field(..., ge=1, description="ID типа района")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания района
class ArialCreate(ArialBase):
    """Схема для создания района"""
    pass

# Схема для обновления района (все поля опциональны)
class ArialUpdate(BaseModel):
    """Схема для обновления района"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    spec_arial_id: Optional[int] = Field(None, ge=1)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и связанными данными)
class ArialResponse(ArialBase):
    """Полная информация о районе"""
    id: int
    spec_arial_name: Optional[str] = Field(None, description="Название типа района")
    organizations_count: Optional[int] = Field(0, description="Количество организаций в районе")
    objects_count: Optional[int] = Field(0, description="Количество объектов в районе")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class ArialListResponse(BaseModel):
    """Краткая информация о районе для списков"""
    id: int
    name: str
    spec_arial_name: Optional[str] = None
    organizations_count: int = 0
    objects_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class ArialOptionResponse(BaseModel):
    """Минимальная информация о районе для выпадающих списков"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)