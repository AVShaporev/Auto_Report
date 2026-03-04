from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема типа населенного пункта
class SpecLocalityBase(BaseModel):
    """Базовая схема типа населенного пункта"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа населенного пункта")
    short_name: Optional[str] = Field(None, max_length=20, description="Краткое наименование (город, село, дер.)")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа населенного пункта
class SpecLocalityCreate(SpecLocalityBase):
    """Схема для создания типа населенного пункта"""
    pass

# Схема для обновления типа населенного пункта (все поля опциональны)
class SpecLocalityUpdate(BaseModel):
    """Схема для обновления типа населенного пункта"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    short_name: Optional[str] = Field(None, max_length=20)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecLocalityResponse(SpecLocalityBase):
    """Полная информация о типе населенного пункта"""
    id: int
    localities_count: Optional[int] = Field(0, description="Количество населенных пунктов этого типа")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecLocalityListResponse(BaseModel):
    """Краткая информация о типе населенного пункта для списков"""
    id: int
    name: str
    short_name: Optional[str] = None
    localities_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecLocalityOptionResponse(BaseModel):
    """Минимальная информация о типе населенного пункта для выпадающих списков"""
    id: int
    name: str
    short_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)