from datetime import datetime, timedelta, timezone

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

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire})
    auth_data = get_auth_data()
    encode_jwt = jwt.encode(to_encode, auth_data['secret_key'], algorithm=auth_data['algorithm'])
    return encode_jwt

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