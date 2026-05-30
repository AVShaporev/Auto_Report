from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime

# Базовая схема организации
class OrganizationBase(BaseModel):
    """Базовая схема организации со всеми полями"""
    name: str = Field(..., min_length=2, max_length=200, description="Наименование организации")
    short_name: str = Field(..., min_length=2, max_length=100, description="Сокращенное наименование")
    inn: str = Field(..., min_length=10, max_length=12, description="ИНН (10 или 12 цифр)")
    kpp: str = Field(..., min_length=9, max_length=9, description="КПП (9 цифр)")
    
    # Руководитель
    director_first_name: str = Field(..., min_length=2, max_length=50, description="Имя руководителя")
    drector_last_name: str = Field(..., min_length=2, max_length=50, description="Фамилия руководителя")
    drector_surname: str = Field(..., min_length=2, max_length=50, description="Отчество руководителя")
    
    # Контакты
    email: Optional[EmailStr] = Field(None, description="Электронная почта")
    telephone: Optional[str] = Field(None, description="Телефон")
    site: Optional[str] = Field(None, description="Веб-сайт")
    
    # Банковские реквизиты
    corr_check: str = Field(..., min_length=20, max_length=20, description="Корреспондентский счет")
    acc_check: str = Field(..., min_length=20, max_length=20, description="Расчетный счет")
    pers_check: str = Field(..., min_length=20, max_length=20, description="Лицевой счет")
    
    # Адрес
    build_number: Optional[str] = Field(None, description="Номер дома")
    room_number: Optional[str] = Field(None, description="Номер помещения")
    postal_code: Optional[str] = Field(None, description="Почтовый индекс")
    
    # Флаги
    customer: bool = Field(False, description="Признак заказчика")
    executor: bool = Field(False, description="Признак подрядчика")
    
    # Внешние ключи
    bank_id: int = Field(..., ge=1, description="ID банка")
    region_id: int = Field(..., ge=1, description="ID региона")
    arial_id: int = Field(..., ge=1, description="ID района")
    locality_id: int = Field(..., ge=1, description="ID населенного пункта")
    street_id: int = Field(..., ge=1, description="ID улицы")
    spec_build_id: int = Field(..., ge=1, description="ID типа строения")
    spec_room_id: Optional[int] = Field(None, ge=1, description="ID типа помещения (опционально)")
    spec_job_title_id: int = Field(..., ge=1, description="ID должности руководителя")
    
    model_config = ConfigDict(from_attributes=True)

# Схема для создания организации
class OrganizationCreate(OrganizationBase):
    """Схема для создания организации (наследует все поля)"""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")

# Схема для обновления организации (все поля опциональны)
class OrganizationUpdate(BaseModel):
    """Схема для обновления организации"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    short_name: Optional[str] = Field(None, min_length=2, max_length=100)
    inn: Optional[str] = Field(None, min_length=10, max_length=12)
    kpp: Optional[str] = Field(None, min_length=9, max_length=9)
    
    director_first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    drector_last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    drector_surname: Optional[str] = Field(None, min_length=2, max_length=50)
    
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    site: Optional[str] = None
    
    corr_check: Optional[str] = Field(None, min_length=20, max_length=20)
    acc_check: Optional[str] = Field(None, min_length=20, max_length=20)
    pers_check: Optional[str] = Field(None, min_length=20, max_length=20)
    
    build_number: Optional[str] = None
    room_number: Optional[str] = None
    postal_code: Optional[str] = None
    
    customer: Optional[bool] = None
    executor: Optional[bool] = None
    
    bank_id: Optional[int] = Field(None, ge=1)
    region_id: Optional[int] = Field(None, ge=1)
    arial_id: Optional[int] = Field(None, ge=1)
    locality_id: Optional[int] = Field(None, ge=1)
    street_id: Optional[int] = Field(None, ge=1)
    spec_build_id: Optional[int] = Field(None, ge=1)
    spec_room_id: Optional[int] = Field(None, ge=1)
    spec_job_title_id: Optional[int] = Field(None, ge=1)
    
    model_config = ConfigDict(from_attributes=True)

# Краткая схема для списка
class OrganizationListResponse(BaseModel):
    """Краткая информация об организации для списков"""
    id: int
    name: str
    short_name: str
    inn: str
    customer: bool
    executor: bool
    bank_name: Optional[str] = None
    region_name: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Полная схема для ответа
class OrganizationResponse(OrganizationBase):
    """Полная информация об организации"""
    id: int
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Связанные объекты (опционально)
    bank: Optional[dict] = None
    region: Optional[dict] = None
    arial: Optional[dict] = None
    locality: Optional[dict] = None
    street: Optional[dict] = None
    spec_build: Optional[dict] = None
    spec_room: Optional[dict] = None
    spec_job_title: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)