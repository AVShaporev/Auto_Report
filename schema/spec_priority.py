from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class SpecPriorityBase(BaseModel):
    """Базовая схема приоритета неисправности"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование приоритета")
    code: str = Field(..., min_length=2, max_length=50, description="Машинный код (low, medium, high, critical, ...)")

    model_config = ConfigDict(from_attributes=True)


class SpecPriorityCreate(SpecPriorityBase):
    """Схема для создания приоритета"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")


class SpecPriorityUpdate(BaseModel):
    """Схема для обновления приоритета (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)


class SpecPriorityResponse(SpecPriorityBase):
    """Полная информация о приоритете"""
    id: int
    is_system: bool = False
    description: Optional[str] = None
    issues_count: Optional[int] = Field(0, description="Количество неисправностей с этим приоритетом")

    model_config = ConfigDict(from_attributes=True)


class SpecPriorityListResponse(BaseModel):
    """Краткая информация о приоритете для списков"""
    id: int
    is_system: bool = False
    name: str
    code: str
    description: Optional[str] = None
    issues_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SpecPriorityOptionResponse(BaseModel):
    """Минимальная информация о приоритете для выпадающих списков"""
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)
