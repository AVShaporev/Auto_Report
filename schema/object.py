from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# Базовая схема объекта
class ObjectBase(BaseModel):
    """Базовая схема объекта"""
    name: str = Field(..., min_length=2, max_length=200, description="Наименование объекта")
    build_number: Optional[str] = Field(None, max_length=50, description="Номер строения")
    room_number: Optional[str] = Field(None, max_length=50, description="Номер помещения")
    responsible_face: str = Field(..., min_length=2, max_length=100, description="Ответственное лицо")
    responsible_faces_contact: str = Field(..., min_length=5, max_length=100, description="Контакты ответственного лица")
    
    # Внешние ключи
    region_id: int = Field(..., ge=1, description="ID региона")
    arial_id: int = Field(..., ge=1, description="ID района")
    locality_id: int = Field(..., ge=1, description="ID населенного пункта")
    street_id: int = Field(..., ge=1, description="ID улицы")
    spec_build_id: int = Field(..., ge=1, description="ID типа строения")
    spec_room_id: Optional[int] = Field(None, ge=1, description="ID типа помещения (опционально)")
    period_id: int = Field(..., ge=1, description="ID периода")
    contract_id: int = Field(..., ge=1, description="ID контракта")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания объекта
class ObjectCreate(ObjectBase):
    """Схема для создания объекта"""
    pass

# Схема для обновления объекта (все поля опциональны)
class ObjectUpdate(BaseModel):
    """Схема для обновления объекта"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    build_number: Optional[str] = Field(None, max_length=50)
    room_number: Optional[str] = Field(None, max_length=50)
    responsible_face: Optional[str] = Field(None, min_length=2, max_length=100)
    responsible_faces_contact: Optional[str] = Field(None, min_length=5, max_length=100)
    
    region_id: Optional[int] = Field(None, ge=1)
    arial_id: Optional[int] = Field(None, ge=1)
    locality_id: Optional[int] = Field(None, ge=1)
    street_id: Optional[int] = Field(None, ge=1)
    spec_build_id: Optional[int] = Field(None, ge=1)
    spec_room_id: Optional[int] = Field(None, ge=1)
    period_id: Optional[int] = Field(None, ge=1)
    contract_id: Optional[int] = Field(None, ge=1)
    
    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и связанными данными)
class ObjectResponse(ObjectBase):
    """Полная информация об объекте"""
    id: int
    
    # Связанные данные (названия)
    region_name: Optional[str] = Field(None, description="Название региона")
    arial_name: Optional[str] = Field(None, description="Название района")
    locality_name: Optional[str] = Field(None, description="Название населенного пункта")
    street_name: Optional[str] = Field(None, description="Название улицы")
    spec_build_name: Optional[str] = Field(None, description="Название типа строения")
    spec_room_name: Optional[str] = Field(None, description="Название типа помещения")
    period_name: Optional[str] = Field(None, description="Название периода")
    contract_number: Optional[str] = Field(None, description="Номер контракта")
    
    # Статистика
    equipments_count: Optional[int] = Field(0, description="Количество оборудования")
    reports_count: Optional[int] = Field(0, description="Количество отчетов")
    orders_count: Optional[int] = Field(0, description="Количество заявок")
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class ObjectListResponse(BaseModel):
    """Краткая информация об объекте для списков"""
    id: int
    name: str
    build_number: Optional[str] = None
    room_number: Optional[str] = None
    responsible_face: str
    region_name: Optional[str] = None
    locality_name: Optional[str] = None
    street_name: Optional[str] = None
    contract_number: Optional[str] = None
    equipments_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Схема для выпадающего списка
class ObjectOptionResponse(BaseModel):
    """Минимальная информация об объекте для выпадающих списков"""
    id: int
    name: str
    address: Optional[str] = Field(None, description="Краткий адрес")
    
    model_config = ConfigDict(from_attributes=True)