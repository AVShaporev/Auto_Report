from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема типа региона
class SpecRegionBase(BaseModel):
    """Базовая схема типа региона"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа региона")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа региона
class SpecRegionCreate(SpecRegionBase):
    """Схема для создания типа региона"""
    description: Optional[str] = Field(None, min_length=2, max_length=500)

# Схема для обновления типа региона (все поля опциональны)
class SpecRegionUpdate(BaseModel):
    """Схема для обновления типа региона"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, min_length=2, max_length=500)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecRegionResponse(SpecRegionBase):
    """Полная информация о типе региона"""
    id: int
    is_system: bool = False
    description: Optional[str] = Field("", description="Описание для типа региона")
    regions_count: Optional[int] = Field(0, description="Количество регионов этого типа")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecRegionListResponse(BaseModel):
    """Краткая информация о типе региона для списков"""
    id: int
    is_system: bool = False
    name: str
    description: Optional[str] = None
    regions_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecRegionOptionResponse(BaseModel):
    """Минимальная информация о типе региона для выпадающих списков"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)