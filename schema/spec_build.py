from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема типа строения
class SpecBuildBase(BaseModel):
    """Базовая схема типа строения"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа строения")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа строения
class SpecBuildCreate(SpecBuildBase):
    """Схема для создания типа строения"""
    pass

# Схема для обновления типа строения (все поля опциональны)
class SpecBuildUpdate(BaseModel):
    """Схема для обновления типа строения"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecBuildResponse(SpecBuildBase):
    """Полная информация о типе строения"""
    id: int
    organizations_count: Optional[int] = Field(0, description="Количество организаций с этим типом строения")
    objects_count: Optional[int] = Field(0, description="Количество объектов с этим типом строения")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecBuildListResponse(BaseModel):
    """Краткая информация о типе строения для списков"""
    id: int
    name: str
    organizations_count: int = 0
    objects_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecBuildOptionResponse(BaseModel):
    """Минимальная информация о типе строения для выпадающих списков"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)