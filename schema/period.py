from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional, List


# Литерал допустимых календарных кодов периода. None → авто-tick игнорирует.
PeriodCode = Literal["monthly", "quarterly", "semiannual", "yearly", "custom"]


# Базовая схема периода
class PeriodBase(BaseModel):
    """Базовая схема периода обслуживания"""
    name: str = Field(..., min_length=2, max_length=100, description="Наименование периода")
    period: str = Field(..., min_length=2, max_length=50, description="Периодичность (месяц, квартал, год)")
    code: Optional[PeriodCode] = Field(
        None,
        description=(
            "Календарный код расписания для авто-генерации плановых заявок: "
            "monthly/quarterly/semiannual/yearly. custom — без авто-tick."
        ),
    )

    model_config = ConfigDict(from_attributes=True)

# Схема для создания периода
class PeriodCreate(PeriodBase):
    """Схема для создания периода"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления периода (все поля опциональны)
class PeriodUpdate(BaseModel):
    """Схема для обновления периода"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    period: Optional[str] = Field(None, min_length=2, max_length=50)
    code: Optional[PeriodCode] = Field(None, description="Календарный код расписания")
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID)
class PeriodResponse(PeriodBase):
    """Полная информация о периоде"""
    id: int
    description: Optional[str] = None
    objects_count: Optional[int] = Field(0, description="Количество объектов с этим периодом")
    reports_count: Optional[int] = Field(0, description="Количество отчетов с этим периодом")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class PeriodListResponse(BaseModel):
    """Краткая информация о периоде для списков"""
    id: int
    name: str
    period: str
    code: Optional[PeriodCode] = None
    description: Optional[str] = None
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