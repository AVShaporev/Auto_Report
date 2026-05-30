from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class OperationBase(BaseModel):
    """Базовая схема операции"""
    name: str = Field(..., min_length=2, max_length=200, description="Наименование операции")
    short_name: Optional[str] = Field(None, max_length=50, description="Короткое наименование (опц.)")
    description: Optional[str] = Field(None, max_length=10000, description="Описание / инструкция")
    period_id: Optional[int] = Field(None, ge=1, description="ID периода обслуживания (опц.)")

    model_config = ConfigDict(from_attributes=True)


class OperationCreate(OperationBase):
    """Схема для создания операции (с привязкой к типам оборудования)"""
    spec_equipment_ids: List[int] = Field(
        default_factory=list,
        description="ID типов оборудования, к которым применима операция"
    )


class OperationUpdate(BaseModel):
    """Схема для обновления операции (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    short_name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=10000)
    period_id: Optional[int] = Field(None, ge=1)
    spec_equipment_ids: Optional[List[int]] = Field(
        None,
        description="Если передан — полностью заменяет список типов оборудования"
    )

    model_config = ConfigDict(from_attributes=True)


class _SpecEquipmentRef(BaseModel):
    """Краткий вложенный объект типа оборудования для ответа"""
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class OperationResponse(OperationBase):
    """Полная информация об операции"""
    id: int
    period_name: Optional[str] = Field(None, description="Наименование периода")
    spec_equipments: List[_SpecEquipmentRef] = Field(
        default_factory=list,
        description="Типы оборудования, к которым применима операция"
    )

    model_config = ConfigDict(from_attributes=True)


class OperationListResponse(BaseModel):
    """Краткая информация об операции для списков"""
    id: int
    name: str
    short_name: Optional[str] = None
    period_id: Optional[int] = None
    period_name: Optional[str] = None
    spec_equipments_count: int = 0
    spec_equipments: List[_SpecEquipmentRef] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OperationOptionResponse(BaseModel):
    """Минимальная информация для выпадающих списков"""
    id: int
    name: str
    short_name: Optional[str] = None
    period_id: Optional[int] = None
    period_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
