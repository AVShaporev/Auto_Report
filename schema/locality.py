from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема населенного пункта
class LocalityBase(BaseModel):
    """Базовая схема населенного пункта"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование населенного пункта")
    spec_locality_id: Optional[int] = Field(None, ge=1, description="ID типа населенного пункта")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания населенного пункта
class LocalityCreate(LocalityBase):
    """Схема для создания населенного пункта"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления населенного пункта (все поля опциональны)
class LocalityUpdate(BaseModel):
    """Схема для обновления населенного пункта"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    spec_locality_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и связанными данными)
class LocalityResponse(LocalityBase):
    """Полная информация о населенном пункте"""
    id: int
    description: Optional[str] = None
    spec_locality_name: Optional[str] = Field(None, description="Название типа населенного пункта")
    spec_locality_short_name: Optional[str] = Field(None, description="Краткое название типа населенного пункта")
    organizations_count: Optional[int] = Field(0, description="Количество организаций в населенном пункте")
    objects_count: Optional[int] = Field(0, description="Количество объектов в населенном пункте")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class LocalityListResponse(BaseModel):
    """Краткая информация о населенном пункте для списков"""
    id: int
    name: str
    spec_locality_name: Optional[str] = None
    description: Optional[str] = None
    organizations_count: int = 0
    objects_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class LocalityOptionResponse(BaseModel):
    """Минимальная информация о населенном пункте для выпадающих списков"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)