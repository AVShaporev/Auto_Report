from datetime import timedelta, datetime
import os

from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from jose import jwt
from passlib.context import CryptContext

from model.user import User
from schema.user import UserRequest
from data import user as data
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_password_hash,
                            verify_password)

from config import settings


# Изменить SECRET_KEY для среды эксплуатации!!!
SECRET_KEY = settings.SECRET_KEY
ALGORITM = settings.ALGORITHM

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def get_hash(plain: str) -> str:
#     """Возврат хеша строки <plain>"""
#     return pwd_context.hash(plain)

# def verify_password(plain: str, hash: str) -> bool:
#     """Хеширование строки <plain> и сравнение ее с
#     записьюю <hash> в БД"""
#     return pwd_context.verify(plain, hash)

def get_jwt_username(token: str) -> str | None:
    """Возврат имени пользователя из jwt-доступа <token>"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITM])
        if not (username := payload.get("sub")):
            return None
    except jwt.JWTError:
        return None
    return username

def get_current_user(token:str) -> User | None:
    """Декодирование токена <token> доступа OAuth
    и возврат объекта User"""
    if not (username := get_jwt_username(token)):
        return None
    if (user := lookup_user(username)):
        return user
    return None

def lookup_user(username: str) -> User | None:
    """Возврат совпадающего пользователя из строки
    <username> из БД"""
    if (user := data.get_one(username)):
        return user
    return None

def auth_user(name: str, plain: str) -> User | None:
    """Аутентификация пользователя <name> и пароля 
    <plain>"""
    if not (user := lookup_user(name)):
        return None
    if not verify_password(plain, user.hash):
        return None
    return user

def create_access_token(data: dict,
                        expires: timedelta | None = None
                        ):
    """Возвращение токена доступа JWT"""
    src = data.copy()
    now = datetime.utcnow()
    if not expires:
        expires = timedelta(minutes=15)
    src.update({'exp': now + expires})
    encoded_jwt = jwt.encode(src, SECRET_KEY,
                                algorithm=ALGORITM)
    return encoded_jwt

def get_one(name: str):
    try:
        id = int(name)
        return data.get_one_by_id(name)
    except:
        name = str(name)
        return data.get_one_by_name(name)


async def create(user_create: UserRequest) -> bool:
    """
    Создание пользователя из Pydantic схемы
    
    Args:
        user_create: Pydantic схема с данными пользователя
    
    Returns:
        bool: True если создан успешно
    """
    # 1. Преобразуем Pydantic модель в SQLAlchemy модель
    user_data = user_create.dict(exclude={'password'})  # исключаем пароль
    
    # 2. Создаем SQLAlchemy модель User
    user = User(
        name=user_data['name'],
        full_name=user_data.get('full_name'),
        email=user_data.get('email'),
        phone=user_data.get('phone'),
        telegram_id=user_data.get('telegram_id'),
        role_id=user_data['role_id'],
        is_active=user_data['is_active'],
        hash=get_password_hash(user_create.password)  # хешируем пароль отдельно
    )
    
    # 3. Передаем SQLAlchemy модель в data слой
    res = await data.create_user(user)
    return res

async def get_all():
    # при отсутвтии в БД суперадмина завести superadmin и в командной 
    # строке указать пароль для него
    if await get_one('superadmin') is None:
        password = input('Введите пароль для пользователя superadmin: ')
        password = password
        await create(name='superadmin',
                        password=password,
                        role_id=1)
    users = await data.get_all()
    return users

def delete_by_name(name:str):
    pass

def delete_by_id(name:str):
    pass


def modify(user: User):
    pass