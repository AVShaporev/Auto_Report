from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема типа улицы
class SpecStreetBase(BaseModel):
    """Базовая схема типа улицы"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа улицы")
    short_name: str = Field(..., min_length=2, max_length=10, description="Сокращенное обозначение типа улицы")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа улицы
class SpecStreetCreate(SpecStreetBase):
    """Схема для создания типа улицы"""
    pass

# Схема для обновления типа улицы (все поля опциональны)
class SpecStreetUpdate(BaseModel):
    """Схема для обновления типа улицы"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    short_name: Optional[str] = Field(None, min_length=2, max_length=10)
    description: Optional[str] = Field(None, min_length=2, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecStreetResponse(SpecStreetBase):
    """Полная информация о типе улицы"""
    id: int
    short_name: Optional[str] = Field(None, min_length=2, max_length=10)
    description: Optional[str] = Field(None, min_length=2, max_length=1000)
    streets_count: Optional[int] = Field(0, description="Количество улиц этого типа")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecStreetListResponse(BaseModel):
    """Краткая информация о типе улицы для списков"""
    id: int
    name: str
    short_name: Optional[str] = Field(None, min_length=2, max_length=10)
    description: Optional[str] = Field(None, min_length=2, max_length=1000)
    streets_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecStreetOptionResponse(BaseModel):
    """Минимальная информация о типе улицы для выпадающих списков"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)