from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SpecReportStatusBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Ру-имя статуса")
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")
    is_default: bool = Field(False, description="Ставится новым отчётам автоматически (может быть ровно у одной строки)")

    model_config = ConfigDict(from_attributes=True)


class SpecReportStatusCreate(SpecReportStatusBase):
    pass


class SpecReportStatusUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    is_default: Optional[bool] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class SpecReportStatusResponse(SpecReportStatusBase):
    """Полная информация о статусе — используется в POST/PUT ответах."""
    id: int
    reports_count: int = Field(0, description="Сколько отчётов используют этот статус")

    model_config = ConfigDict(from_attributes=True)


class SpecReportStatusListResponse(BaseModel):
    """Для списков (пагинация)."""
    id: int
    name: str
    description: Optional[str] = None
    is_default: bool = False
    reports_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SpecReportStatusOptionResponse(BaseModel):
    """Для селектов/фильтров на фронтах — минимальная информация."""
    id: int
    name: str
    description: Optional[str] = None
    is_default: bool = False

    model_config = ConfigDict(from_attributes=True)
