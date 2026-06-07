from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема типа района
class SpecArialBase(BaseModel):
    """Базовая схема типа района"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа района")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа района
class SpecArialCreate(SpecArialBase):
    """Схема для создания типа района"""
    pass

# Схема для обновления типа района (все поля опциональны)
class SpecArialUpdate(BaseModel):
    """Схема для обновления типа района"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, min_length=2, max_length=500)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecArialResponse(SpecArialBase):
    """Полная информация о типе района"""
    id: int
    description: Optional[str] = Field(None, max_length=500, description="Описание типа района")
    arials_count: Optional[int] = Field(0, description="Количество районов этого типа")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecArialListResponse(BaseModel):
    """Краткая информация о типе района для списков"""
    id: int
    name: str
    description: Optional[str] = None
    arials_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecArialOptionResponse(BaseModel):
    """Минимальная информация о типе района для выпадающих списков"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)