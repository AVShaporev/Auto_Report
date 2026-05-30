from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема банка
class BankBase(BaseModel):
    """Базовая схема банка"""
    name: str = Field(..., min_length=2, max_length=200, description="Наименование банка")
    bik: str = Field(..., min_length=9, max_length=9, description="БИК (9 цифр)")
    inn: str = Field(..., min_length=10, max_length=12, description="ИНН банка")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания банка
class BankCreate(BankBase):
    """Схема для создания банка"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления банка (все поля опциональны)
class BankUpdate(BaseModel):
    """Схема для обновления банка"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    bik: Optional[str] = Field(None, min_length=9, max_length=9)
    inn: Optional[str] = Field(None, min_length=10, max_length=12)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class BankResponse(BankBase):
    """Полная информация о банке"""
    id: int
    description: Optional[str] = None
    organizations_count: Optional[int] = Field(0, description="Количество организаций, использующих этот банк")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class BankListResponse(BaseModel):
    """Краткая информация о банке для списков"""
    id: int
    name: str
    bik: str
    inn: str
    description: Optional[str] = None
    organizations_count: int = 0

    model_config = ConfigDict(from_attributes=True)