from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date

# Базовая схема дополнительного соглашения
class SubContractBase(BaseModel):
    """Базовая схема дополнительного соглашения"""
    number: str = Field(..., min_length=1, max_length=50, description="Номер дополнительного соглашения")
    date_of_consclusion: date = Field(..., description="Дата заключения")
    subject: str = Field(..., min_length=3, max_length=500, description="Предмет дополнительного соглашения")
    contract_id: int = Field(..., ge=1, description="ID основного контракта")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания дополнительного соглашения
class SubContractCreate(BaseModel):
    """Схема для создания дополнительного соглашения"""
    number: str = Field(..., min_length=1, max_length=50, description="Номер дополнительного соглашения")
    date_of_consclusion: date = Field(..., description="Дата заключения")
    subject: str = Field(..., min_length=3, max_length=500, description="Предмет дополнительного соглашения")
    contract_id: int = Field(..., ge=1, description="ID основного контракта")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для обновления дополнительного соглашения (все поля опциональны)
class SubContractUpdate(BaseModel):
    """Схема для обновления дополнительного соглашения"""
    number: Optional[str] = Field(None, min_length=1, max_length=50)
    date_of_consclusion: Optional[date] = None
    subject: Optional[str] = Field(None, min_length=3, max_length=500)
    contract_id: Optional[int] = Field(None, ge=1)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и связанными данными)
class SubContractResponse(SubContractBase):
    """Полная информация о дополнительном соглашении"""
    id: int
    contract_number: Optional[str] = Field(None, description="Номер основного контракта")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SubContractListResponse(BaseModel):
    """Краткая информация о дополнительном соглашении для списков"""
    id: int
    number: str
    date_of_consclusion: date
    subject: str
    contract_number: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class SubContractOptionResponse(BaseModel):
    """Минимальная информация о дополнительном соглашении для выпадающих списков"""
    id: int
    number: str
    subject: str
    
    model_config = ConfigDict(from_attributes=True)