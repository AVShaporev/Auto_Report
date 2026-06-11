from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


# Базовая схема типа журнала
class SpecJournalBase(BaseModel):
    """Базовая схема типа журнала"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа журнала")
    short_name: Optional[str] = Field(None, max_length=50, description="Краткое наименование")
    code: Optional[str] = Field(None, min_length=2, max_length=50, description="Машинный код (maintenance, fire_protection, ...)")

    model_config = ConfigDict(from_attributes=True)


# Схема для создания типа журнала
class SpecJournalCreate(SpecJournalBase):
    """Схема для создания типа журнала"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")


# Схема для обновления типа журнала (все поля опциональны)
class SpecJournalUpdate(BaseModel):
    """Схема для обновления типа журнала"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    short_name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)


# Полная схема для ответа
class SpecJournalResponse(SpecJournalBase):
    """Полная информация о типе журнала"""
    id: int
    is_system: bool = False
    description: Optional[str] = None
    template_filename: Optional[str] = Field(None, description="Оригинальное имя файла шаблона документа (если привязан)")

    model_config = ConfigDict(from_attributes=True)


# Краткая схема для списка
class SpecJournalListResponse(BaseModel):
    """Краткая информация о типе журнала для списков"""
    id: int
    is_system: bool = False
    name: str
    short_name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    template_filename: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Схема для выпадающего списка
class SpecJournalOptionResponse(BaseModel):
    """Минимальная информация о типе журнала для выпадающих списков"""
    id: int
    name: str
    short_name: Optional[str] = None
    code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
