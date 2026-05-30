from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# Базовая схема статуса неисправности
class SpecStatusBase(BaseModel):
    """Базовая схема статуса неисправности"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование статуса")
    code: str = Field(..., min_length=2, max_length=50, description="Машинный код статуса (new, in_progress, resolved, closed, ...)")

    model_config = ConfigDict(from_attributes=True)

# Схема для создания статуса
class SpecStatusCreate(SpecStatusBase):
    """Схема для создания статуса неисправности"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления статуса (все поля опциональны)
class SpecStatusUpdate(BaseModel):
    """Схема для обновления статуса неисправности"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecStatusResponse(SpecStatusBase):
    """Полная информация о статусе неисправности"""
    id: int
    description: Optional[str] = None
    issues_count: Optional[int] = Field(0, description="Количество неисправностей с этим статусом")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecStatusListResponse(BaseModel):
    """Краткая информация о статусе для списков"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    issues_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecStatusOptionResponse(BaseModel):
    """Минимальная информация о статусе для выпадающих списков"""
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)
