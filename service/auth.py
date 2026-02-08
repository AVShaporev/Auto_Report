from typing import Any, Union, Optional, Dict
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from fastapi import Depends, Request, HTTPException, status
from passlib.context import CryptContext
from jose import jwt
from jose.exceptions import JWTError
# from pydantic import EmailStr

from config import get_auth_data
from model.dao import UsersDAO
from model.user import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# def create_access_token(data: dict) -> str:

#     del data['_sa_instance_state']
#     to_encode = data.copy()
#     expire = datetime.now(timezone.utc) + timedelta(days=30)

#     to_encode.update({"exp": expire})
#     auth_data = get_auth_data()


#     to_encode = json.dumps(to_encode)

#     encode_jwt = jwt.encode(to_encode, auth_data['secret_key'], algorithm=auth_data['algorithm'])

#     return encode_jwt



def create_access_token(
    subject: Union[str, Any], 
    expires_delta: timedelta = None,
    token_type: str = "access"
) -> str:

    # Подгорузка переменных окружения
    auth_data = get_auth_data()

    # 1. Определение времени истечения токена
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=auth_data['access_token_expire_minutes']
        )
    
    # 2. Формирование payload (данных внутри токена)
    to_encode = {
        "exp": expire,  # Время истечения (обязательное поле для JWT)
        "sub": str(subject),  # Subject (обычно user_id или username)
        "type": token_type  # Тип токена (access или refresh)
    }
    
    # 3. Кодирование токена
    encoded_jwt = jwt.encode(
        to_encode, 
        auth_data['secret_key'], 
        algorithm=auth_data['algorithm']
    )
    return encoded_jwt

def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: timedelta = None,
    additional_claims: Optional[Dict] = None
) -> str:
    """
    Создает refresh токен для обновления access токенов
    
    Args:
        subject: Идентификатор пользователя (username/user_id)
        expires_delta: Время жизни refresh токена (обычно дни/недели)
        additional_claims: Дополнительные данные для включения в токен
    
    Returns:
        JWT refresh токен
    """

    # Подгорузка переменных окружения
    auth_data = get_auth_data()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # По умолчанию используем длительный срок (дни/недели)
        expire = datetime.utcnow() + timedelta(days=auth_data['refresh_token_expire_days'])
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",  # Ключевое отличие от access токена
        "iat": datetime.utcnow(),
        "jti": str(uuid4()),  # Уникальный идентификатор токена
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    return jwt.encode(
        to_encode,
        auth_data['secret_key'], 
        algorithm=auth_data['algorithm']
    )

async def authenticate_user(login: str, password: str):
    user = await UsersDAO.find_one_or_none({'name': login})
    if not user or verify_password(plain_password=password, hashed_password=user[0].hash) is False:
        return None
    return user

def get_token(request: Request):
    token = request.cookies.get('users_access_token')
    if not token:
        return None
        # raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token not found')
    return token

async def get_current_user(token: str | None = Depends(get_token)):
    if token:
        try:
            auth_data = get_auth_data()
            payload = jwt.decode(token, auth_data['secret_key'], algorithms=[auth_data['algorithm']])
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Токен не валидный!')

        expire = payload.get('exp')
        expire_time = datetime.fromtimestamp(int(expire), tz=timezone.utc)
        if (not expire) or (expire_time < datetime.now(timezone.utc)):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Токен истек')

        user_id = payload.get('sub')

        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Не найден ID пользователя')

        user = await UsersDAO.find_one_or_none_by_id(int(user_id))

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')

        return user
    
    return None



async def get_current_admin_user(current_user: User = Depends(get_current_user)):


    return current_user
    # if current_user:
    #     if current_user.name == 'superadmin':
    #         return current_user
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Недостаточно прав!')
    # return None