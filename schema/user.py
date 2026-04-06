from datetime import datetime
from typing import Optional, List

from pydantic import ConfigDict, BaseModel, Field, EmailStr

# from model.user import User
from schema.role import RoleResponse, RoleSimpleResponse


# модель чтения пользователя из БД
class Read_User(BaseModel):
    # id: int
    model_config = ConfigDict(from_attributes=True)

# class UserLogin(BaseModel):
#     id: int
#     name: str
#     full_name: Optional[str] = None
#     role: Optional[RoleSimpleResponse] = None

#     model_config = ConfigDict(from_attributes=True)

# модель аунтентификации
class SUserAuth(BaseModel):
    login: str = Field(..., description="Имя пользователя")
    password: str = Field(..., min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")

    model_config = ConfigDict(from_attributes=True)

# Базовая схема пользователя
class UserBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[str] = None
    role_id: int = Field(..., ge=1)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)

# Схема для создания пользователя
class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

    model_config = ConfigDict(from_attributes=True)

# Схема для обновления пользователя (все поля опциональны)
class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    telegram_id: Optional[str] = None
    role_id: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)

    model_config = ConfigDict(from_attributes=True)

# Схема для ответа (с ID и отношениями)
class UserResponse(UserBase):
    id: int
    name: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role_id: int
    is_active: bool
    role: Optional[RoleSimpleResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

class UserRequest(UserBase):
    name: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

# Схема для списка пользователей (без чувствительных данных)
class UserListResponse(BaseModel):
    id: int
    name: str
    full_name: Optional[str] = None
    email: Optional[str] = Field(None, validate_default=True)
    role_name: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True

class UserInDB(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[str] = None
    role_id: int = Field(..., ge=1)
    is_active: bool = True
    role: Optional[RoleSimpleResponse] = None

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    user: UserLogin
    access_token: str
    refresh_token: str

    model_config = ConfigDict(from_attributes=True)

