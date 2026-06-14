from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date

# Базовая схема заявки (без user_id)
class OrderBase(BaseModel):
    """Базовая схема заявки"""
    number: str = Field(..., min_length=1, max_length=200, description="Номер заявки")
    spec_order_id: int = Field(..., ge=1, description="ID типа заявки")
    contract_id: int = Field(..., ge=1, description="ID контракта")
    object_id: int = Field(..., ge=1, description="ID объекта")
    description: Optional[str] = Field(None, max_length=1000, description="Описание заявки")
    status: str = Field("new", description="Статус заявки (new, in_progress, completed, cancelled)")

    model_config = ConfigDict(from_attributes=True)

# Схема для создания заявки (без user_id и без number — номер генерится сервером)
class OrderCreate(BaseModel):
    """Схема для создания заявки.

    Номер генерируется сервером по маске
    "{object.number_in_contract}/{MM}/{YYYY}/{customer.short_name}/{contract.short_subject}/{seq}",
    где seq — порядковый номер заявки для пары (object, contract) среди всех её заявок.
    """
    spec_order_id: int = Field(..., ge=1, description="ID типа заявки")
    contract_id: int = Field(..., ge=1, description="ID контракта")
    object_id: int = Field(..., ge=1, description="ID объекта")
    description: Optional[str] = Field(None, max_length=1000, description="Описание заявки")
    status: str = Field("new", description="Статус заявки")

    model_config = ConfigDict(from_attributes=True)

# Схема для обновления заявки (все поля опциональны)
class OrderUpdate(BaseModel):
    """Схема для обновления заявки"""
    number: Optional[str] = Field(None, min_length=1, max_length=200)
    spec_order_id: Optional[int] = Field(None, ge=1)
    contract_id: Optional[int] = Field(None, ge=1)
    object_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, description="Статус заявки")

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и связанными данными) - оставляем user_id для отображения
class OrderResponse(OrderBase):
    """Полная информация о заявке"""
    id: int
    user_id: int = Field(..., description="ID пользователя, создавшего заявку")
    report_id: Optional[int] = Field(None, description="ID отчета")
    created_at: date = Field(..., description="Дата создания")
    period_start_date: Optional[date] = Field(
        None,
        description="Начало периода обслуживания (только для авто-сгенерированных плановых заявок)",
    )

    # Связанные данные
    spec_order_name: Optional[str] = Field(None, description="Название типа заявки")
    contract_number: Optional[str] = Field(None, description="Номер контракта")
    object_name: Optional[str] = Field(None, description="Название объекта")
    user_name: Optional[str] = Field(None, description="Имя пользователя")
    report_number: Optional[str] = Field(None, description="Номер отчета")

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class OrderListResponse(BaseModel):
    """Краткая информация о заявке для списков"""
    id: int
    number: str
    created_at: date
    status: str
    report_id: Optional[int] = None

    # FK-id'шники для фронта (фильтрация по типу/контракту/объекту,
    # деривация period_id при создании отчёта без отдельного GET)
    spec_order_id: Optional[int] = None
    contract_id: Optional[int] = None
    object_id: Optional[int] = None
    period_id: Optional[int] = None

    spec_order_name: Optional[str] = None
    object_name: Optional[str] = None
    user_name: Optional[str] = None
    contract_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class OrderOptionResponse(BaseModel):
    """Минимальная информация о заявке для выпадающих списков"""
    id: int
    number: str
    status: str
    
    model_config = ConfigDict(from_attributes=True)