from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема должности руководителя
class SpecJobTitleBase(BaseModel):
    """Базовая схема должности руководителя"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование должности руководителя")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания должности руководителя
class SpecJobTitleCreate(SpecJobTitleBase):
    """Схема для создания должности руководителя"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления должности руководителя (все поля опциональны)
class SpecJobTitleUpdate(BaseModel):
    """Схема для обновления должности руководителя"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class SpecJobTitleResponse(SpecJobTitleBase):
    """Полная информация о должности руководителя"""
    id: int
    is_system: bool = False
    description: Optional[str] = None
    organizations_count: Optional[int] = Field(0, description="Количество организаций с этой должностью")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class SpecJobTitleListResponse(BaseModel):
    """Краткая информация о должности руководителя для списков"""
    id: int
    is_system: bool = False
    name: str
    description: Optional[str] = None
    organizations_count: int = 0

    model_config = ConfigDict(from_attributes=True)