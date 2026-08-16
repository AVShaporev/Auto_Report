from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SpecOrderStatusBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Ру-имя статуса")
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")
    is_default: bool = Field(False, description="Ставится новым заявкам автоматически (может быть ровно у одной строки)")

    model_config = ConfigDict(from_attributes=True)


class SpecOrderStatusCreate(SpecOrderStatusBase):
    pass


class SpecOrderStatusUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    is_default: Optional[bool] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class SpecOrderStatusResponse(SpecOrderStatusBase):
    """Полная информация о статусе — используется в POST/PUT ответах."""
    id: int
    orders_count: int = Field(0, description="Сколько заявок используют этот статус")

    model_config = ConfigDict(from_attributes=True)


class SpecOrderStatusListResponse(BaseModel):
    """Для списков (пагинация)."""
    id: int
    name: str
    description: Optional[str] = None
    is_default: bool = False
    orders_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SpecOrderStatusOptionResponse(BaseModel):
    """Для селектов/фильтров на фронтах — минимальная информация."""
    id: int
    name: str
    description: Optional[str] = None
    is_default: bool = False

    model_config = ConfigDict(from_attributes=True)
