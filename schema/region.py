from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема региона
class RegionBase(BaseModel):
    """Базовая схема региона"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование региона")
    symbol: str = Field(..., min_length=2, max_length=10, description="Символьный код региона")
    spec_region_id: int = Field(..., ge=1, description="ID типа региона")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания региона
class RegionCreate(RegionBase):
    """Схема для создания региона"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления региона (все поля опциональны)
class RegionUpdate(BaseModel):
    """Схема для обновления региона"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    symbol: Optional[str] = Field(None, min_length=2, max_length=10)
    spec_region_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и связанными данными)
class RegionResponse(RegionBase):
    """Полная информация о регионе"""
    id: int
    description: Optional[str] = None
    spec_region_name: Optional[str] = Field(None, description="Название типа региона")
    organizations_count: Optional[int] = Field(0, description="Количество организаций в регионе")
    objects_count: Optional[int] = Field(0, description="Количество объектов в регионе")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class RegionListResponse(BaseModel):
    """Краткая информация о регионе для списков"""
    id: int
    name: str
    symbol: str
    spec_region_name: Optional[str] = None
    description: Optional[str] = None
    organizations_count: int = 0
    objects_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка (самая краткая)
class RegionOptionResponse(BaseModel):
    """Минимальная информация о регионе для выпадающих списков"""
    id: int
    name: str
    symbol: str
    
    model_config = ConfigDict(from_attributes=True)