from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема типа заявки
class SpecOrderBase(BaseModel):
    """Базовая схема типа заявки"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа заявки")
    short_name: Optional[str] = Field(None, max_length=50, description="Краткое наименование")
    code: Optional[str] = Field(None, min_length=2, max_length=50, description="Машинный код (emergency, primary, planned, test, ...)")

    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа заявки
class SpecOrderCreate(SpecOrderBase):
    """Схема для создания типа заявки"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления типа заявки (все поля опциональны)
class SpecOrderUpdate(BaseModel):
    """Схема для обновления типа заявки"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    short_name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecOrderResponse(SpecOrderBase):
    """Полная информация о типе заявки"""
    id: int
    is_system: bool = False
    description: Optional[str] = None
    orders_count: Optional[int] = Field(0, description="Количество заявок этого типа")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecOrderListResponse(BaseModel):
    """Краткая информация о типе заявки для списков"""
    id: int
    is_system: bool = False
    name: str
    short_name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    orders_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SpecOrderOptionResponse(BaseModel):
    """Минимальная информация о типе заявки для выпадающих списков"""
    id: int
    name: str
    short_name: Optional[str] = None
    code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)