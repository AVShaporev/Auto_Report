from typing import Any, Union, Optional, Dict
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import jwt
from jose.exceptions import JWTError

from config import get_auth_data
from model.dao import UsersDAO  # исправленный импорт
from model.user import User

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(
    subject: Union[str, Any],
    expires_delta: timedelta = None,
    token_type: str = "access"
) -> str:
    auth_data = get_auth_data()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=auth_data['access_token_expire_minutes']
        )
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": token_type
    }
    return jwt.encode(to_encode, auth_data['secret_key'], algorithm=auth_data['algorithm'])

def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: timedelta = None,
    additional_claims: Optional[Dict] = None
) -> str:
    auth_data = get_auth_data()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=auth_data['refresh_token_expire_days']
        )
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid4()),
    }
    if additional_claims:
        to_encode.update(additional_claims)
    return jwt.encode(to_encode, auth_data['secret_key'], algorithm=auth_data['algorithm'])

async def authenticate_user(login: str, password: str) -> Optional[User]:
    """
    Аутентифицирует пользователя по логину (name) и паролю.
    Возвращает объект User или None.
    """
    # Ищем пользователя по полю name (логин)
    user = await UsersDAO.find_with_role(name=login)
    if not user or not verify_password(password, user.hash):
        return None
    return user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = credentials.credentials
    auth_data = get_auth_data()
    try:
        payload = jwt.decode(token, auth_data['secret_key'], algorithms=[auth_data['algorithm']])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен не валидный")

    expire = payload.get('exp')
    if not expire:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен не содержит срока действия")
    expire_time = datetime.fromtimestamp(int(expire), tz=timezone.utc)
    if expire_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен истёк")

    if payload.get('type') != 'access':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный тип токена")

    user_name = payload.get('sub')
    if not user_name:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не найден идентификатор пользователя")

    user = await UsersDAO.find_one_or_none(name=str(user_name))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return user

# Для проверки админских прав используется role.is_admin / role.is_superadmin
# (поля хранятся на модели Role, НЕ на User). Канонический путь в коде —
# прямая проверка: `if not current_user.role.is_admin: raise HTTPException(...)`.
# Либо фабрики зависимостей в core/dependencies.py (require_role_read и т.п.).