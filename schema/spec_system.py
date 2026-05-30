from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


# ========== БАЗОВАЯ СХЕМА ==========

class SpecSystemBase(BaseModel):
    """Базовая схема типа обслуживаемой системы"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование")
    short_name: Optional[str] = Field(None, max_length=50, description="Сокращённое наименование")
    is_fire_protection: bool = Field(
        False,
        description="Принадлежность к средствам и системам противопожарной защиты",
    )

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ СОЗДАНИЯ ==========

class SpecSystemCreate(SpecSystemBase):
    """Схема для создания типа системы"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")


# ========== СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ ==========

class SpecSystemUpdate(BaseModel):
    """Схема для обновления типа системы (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    short_name: Optional[str] = Field(None, max_length=50)
    is_fire_protection: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОТВЕТА ==========

class SpecSystemResponse(SpecSystemBase):
    """Полная информация о типе системы"""
    id: int
    description: Optional[str] = None
    objects_equipments_count: int = Field(
        0, description="Количество связанных записей объект-оборудование",
    )

    model_config = ConfigDict(from_attributes=True)


# ========== КРАТКАЯ СХЕМА ДЛЯ СПИСКА ==========

class SpecSystemListResponse(BaseModel):
    """Краткая информация о типе системы для списков"""
    id: int
    name: str
    short_name: Optional[str] = None
    is_fire_protection: bool
    description: Optional[str] = None
    objects_equipments_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМА ДЛЯ ВЫПАДАЮЩЕГО СПИСКА ==========

class SpecSystemOptionResponse(BaseModel):
    """Минимальная информация о типе системы для выпадающих списков"""
    id: int
    name: str
    short_name: Optional[str] = None
    is_fire_protection: bool

    model_config = ConfigDict(from_attributes=True)
