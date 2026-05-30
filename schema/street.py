from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема улицы
class StreetBase(BaseModel):
    """Базовая схема улицы"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование улицы")
    spec_street_id: int = Field(..., ge=1, description="ID типа улицы")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания улицы
class StreetCreate(StreetBase):
    """Схема для создания улицы"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления улицы (все поля опциональны)
class StreetUpdate(BaseModel):
    """Схема для обновления улицы"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    spec_street_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и связанными данными)
class StreetResponse(StreetBase):
    """Полная информация об улице"""
    id: int
    description: Optional[str] = None
    spec_street_name: Optional[str] = Field(None, description="Название типа улицы")
    organizations_count: Optional[int] = Field(0, description="Количество организаций на улице")
    objects_count: Optional[int] = Field(0, description="Количество объектов на улице")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class StreetListResponse(BaseModel):
    """Краткая информация об улице для списков"""
    id: int
    name: str
    spec_street_name: Optional[str] = None
    description: Optional[str] = None
    organizations_count: int = 0
    objects_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class StreetOptionResponse(BaseModel):
    """Минимальная информация об улице для выпадающих списков"""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)