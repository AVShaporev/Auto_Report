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
    status_id: Optional[int] = Field(None, ge=1, description="ID статуса (spec_order_statuses.id)")

    model_config = ConfigDict(from_attributes=True)

# Схема для создания заявки (без user_id и без number — номер генерится сервером)
class OrderCreate(BaseModel):
    """Схема для создания заявки.

    Номер генерируется сервером по маске
    "{object.number_in_contract}/{MM}/{YYYY}/{customer.short_name}/{contract.short_subject}/{spec_order.short_name}/{seq}".
    status_id опционально; None → берётся дефолтный (spec_order_statuses.is_default=true).
    """
    spec_order_id: int = Field(..., ge=1, description="ID типа заявки")
    contract_id: int = Field(..., ge=1, description="ID контракта")
    object_id: int = Field(..., ge=1, description="ID объекта")
    description: Optional[str] = Field(None, max_length=1000, description="Описание заявки")
    status_id: Optional[int] = Field(None, ge=1, description="ID статуса (spec_order_statuses.id); None → дефолт")
    assigned_to_id: Optional[int] = Field(
        None, ge=1, description="ID ответственного (users.id); может быть не назначен"
    )
    # Срок исполнения. Если не передан — сервис посчитает по spec_order.sla_kind
    # (periodic → конец периода, from_creation → created_at + sla_days,
    # manual → NULL). Явно переданный due_date перекрывает авто-расчёт.
    due_date: Optional[date] = Field(
        None, description="Срок исполнения; None → авто по sla_kind типа"
    )

    model_config = ConfigDict(from_attributes=True)

# Схема для обновления заявки (все поля опциональны)
class OrderUpdate(BaseModel):
    """Схема для обновления заявки"""
    number: Optional[str] = Field(None, min_length=1, max_length=200)
    spec_order_id: Optional[int] = Field(None, ge=1)
    contract_id: Optional[int] = Field(None, ge=1)
    object_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000)
    status_id: Optional[int] = Field(None, ge=1, description="ID статуса (spec_order_statuses.id)")
    # ge=0 (не ge=1!) — 0 (или явный null) в PATCH означает «снять
    # ответственного». `exclude_unset=True` в service отличает «не
    # передано» от «сброс в null».
    assigned_to_id: Optional[int] = Field(
        None, ge=0, description="ID ответственного; 0/null → снять"
    )
    # PATCH due_date: явное значение — установить, отсутствие ключа —
    # оставить как было. Чтобы «сбросить в null», клиент передаёт
    # `due_date: null` (это отличается от не-передачи через exclude_unset).
    due_date: Optional[date] = Field(None, description="Срок исполнения")

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и связанными данными) - оставляем user_id для отображения
class OrderResponse(BaseModel):
    """Полная информация о заявке"""
    id: int
    number: str
    spec_order_id: int
    contract_id: int
    object_id: int
    description: Optional[str] = None
    status_id: int
    status_name: Optional[str] = Field(None, description="Ру-имя статуса из справочника")
    user_id: int = Field(..., description="ID пользователя, создавшего заявку")
    report_id: Optional[int] = Field(None, description="ID отчета")
    created_at: date = Field(..., description="Дата создания")
    period_start_date: Optional[date] = Field(
        None,
        description="Начало периода обслуживания (только для авто-сгенерированных плановых заявок)",
    )
    due_date: Optional[date] = Field(
        None, description="Срок исполнения (для температурной шкалы во фронте)"
    )

    # Связанные данные
    spec_order_name: Optional[str] = Field(None, description="Название типа заявки")
    contract_number: Optional[str] = Field(None, description="Номер контракта")
    object_name: Optional[str] = Field(None, description="Название объекта")
    user_name: Optional[str] = Field(None, description="Имя пользователя (автор)")
    assigned_to_id: Optional[int] = Field(None, description="ID ответственного")
    assigned_to_name: Optional[str] = Field(None, description="Имя ответственного")
    report_number: Optional[str] = Field(None, description="Номер отчета")
    report_status_name: Optional[str] = Field(
        None, description="Ру-имя статуса связанного отчёта (для отчётного маркера)"
    )

    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class OrderListResponse(BaseModel):
    """Краткая информация о заявке для списков"""
    id: int
    number: str
    created_at: date
    due_date: Optional[date] = None
    status_id: int
    status_name: Optional[str] = None
    report_id: Optional[int] = None
    report_status_name: Optional[str] = None

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
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class OrderOptionResponse(BaseModel):
    """Минимальная информация о заявке для выпадающих списков"""
    id: int
    number: str
    status_id: int
    status_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
