from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема типа договора
class SpecContractBase(BaseModel):
    """Базовая схема типа договора"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование типа договора")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания типа договора
class SpecContractCreate(SpecContractBase):
    """Схема для создания типа договора"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления типа договора (все поля опциональны)
class SpecContractUpdate(BaseModel):
    """Схема для обновления типа договора"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecContractResponse(SpecContractBase):
    """Полная информация о типе договора"""
    id: int
    is_system: bool = False
    description: Optional[str] = None
    contracts_count: Optional[int] = Field(0, description="Количество договоров этого типа")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecContractListResponse(BaseModel):
    """Краткая информация о типе договора для списков"""
    id: int
    is_system: bool = False
    name: str
    description: Optional[str] = None
    contracts_count: int = 0

    model_config = ConfigDict(from_attributes=True)