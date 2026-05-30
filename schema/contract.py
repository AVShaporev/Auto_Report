from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime

# Базовая схема контракта
class ContractBase(BaseModel):
    """Базовая схема контракта"""
    number: str = Field(..., min_length=1, max_length=50, description="Номер контракта")
    date_of_consclusion: date = Field(..., description="Дата заключения")
    date_of_completion: date = Field(..., description="Дата завершения")
    summ: float = Field(..., gt=0, description="Сумма контракта")
    subject: str = Field(..., min_length=3, max_length=500, description="Предмет контракта")
    short_subject: str = Field(..., min_length=3, max_length=200, description="Краткий предмет контракта")
    type_contract: str = Field(..., min_length=2, max_length=50, description="Тип контракта")
    spec_contract_id: int = Field(..., ge=1, description="ID типа контракта")
    customer_id: int = Field(..., ge=1, description="ID организации-заказчика")
    executor_id: int = Field(..., ge=1, description="ID организации-подрядчика")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания контракта
class ContractCreate(ContractBase):
    """Схема для создания контракта"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления контракта (все поля опциональны)
class ContractUpdate(BaseModel):
    """Схема для обновления контракта"""
    number: Optional[str] = Field(None, min_length=1, max_length=50)
    date_of_consclusion: Optional[date] = None
    date_of_completion: Optional[date] = None
    summ: Optional[float] = Field(None, gt=0)
    subject: Optional[str] = Field(None, min_length=3, max_length=500)
    short_subject: Optional[str] = Field(None, min_length=3, max_length=200)
    type_contract: Optional[str] = Field(None, min_length=2, max_length=50)
    spec_contract_id: Optional[int] = Field(None, ge=1)
    customer_id: Optional[int] = Field(None, ge=1)
    executor_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и связанными данными)
class ContractResponse(ContractBase):
    """Полная информация о контракте"""
    id: int
    description: Optional[str] = None

    # Связанные данные
    spec_contract_name: Optional[str] = Field(None, description="Название типа контракта")
    customer_name: Optional[str] = Field(None, description="Название организации-заказчика")
    executor_name: Optional[str] = Field(None, description="Название организации-подрядчика")
    
    # Статистика
    sub_contracts_count: Optional[int] = Field(0, description="Количество дополнительных соглашений")
    objects_count: Optional[int] = Field(0, description="Количество объектов")
    reports_count: Optional[int] = Field(0, description="Количество отчетов")
    orders_count: Optional[int] = Field(0, description="Количество заявок")
    issues_count: Optional[int] = Field(0, description="Количество неисправностей")

    # Метаданные (из Base)
    created_at: Optional[datetime] = Field(None, description="Дата создания записи")
    updated_at: Optional[datetime] = Field(None, description="Дата последнего обновления записи")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class ContractListResponse(BaseModel):
    """Краткая информация о контракте для списков"""
    id: int
    number: str
    date_of_consclusion: date
    date_of_completion: date
    summ: float
    short_subject: str
    type_contract: str
    spec_contract_name: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    executor_id: Optional[int] = None
    executor_name: Optional[str] = None
    description: Optional[str] = None
    objects_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class ContractOptionResponse(BaseModel):
    """Минимальная информация о контракте для выпадающих списков"""
    id: int
    number: str
    short_subject: str
    
    model_config = ConfigDict(from_attributes=True)