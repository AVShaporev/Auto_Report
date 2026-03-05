from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема периода
class PeriodBase(BaseModel):
    """Базовая схема периода обслуживания"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование периода")
    period: str = Field(..., min_length=2, max_length=50, description="Периодичность (месяц, квартал, год)")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания периода
class PeriodCreate(PeriodBase):
    """Схема для создания периода"""
    pass

# Схема для обновления периода (все поля опциональны)
class PeriodUpdate(BaseModel):
    """Схема для обновления периода"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    period: Optional[str] = Field(None, min_length=2, max_length=50)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class PeriodResponse(PeriodBase):
    """Полная информация о периоде"""
    id: int
    objects_count: Optional[int] = Field(0, description="Количество объектов с этим периодом")
    reports_count: Optional[int] = Field(0, description="Количество отчетов с этим периодом")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class PeriodListResponse(BaseModel):
    """Краткая информация о периоде для списков"""
    id: int
    name: str
    period: str
    objects_count: int = 0
    reports_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class PeriodOptionResponse(BaseModel):
    """Минимальная информация о периоде для выпадающих списков"""
    id: int
    name: str
    period: str
    
    model_config = ConfigDict(from_attributes=True)