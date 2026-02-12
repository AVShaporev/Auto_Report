from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, BaseModel, Field, EmailStr

from model.user import User
from schema.role import RoleResponse


# модель чтения пользователя из БД
class Read_User(BaseModel):
    # id: int
    model_config = ConfigDict(from_attribures=True)

# модель аунтентификации
class SUserAuth(BaseModel):
    login: str = Field(..., description="Имя пользователя")
    password: str = Field(..., min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")



class UserBase(BaseModel):
    id:int
    name: str = None
    role_id: int = None
    is_active: bool = None
    role: Optional[RoleResponse] = None

    model_config = ConfigDict(from_attributes=True)

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: str = None
    password: str = None

class UserInDB(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    user: UserBase
    access_token: str
    refresh_token: str

