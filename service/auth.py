from typing import Any, Union, Optional, Dict, Tuple
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_auth_data
from model.dao import UsersDAO  # исправленный импорт
from model.user import User
from model.user_session import UserSession
from data import user_session as user_session_dao

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
    additional_claims: Optional[Dict] = None,
    jti: Optional[str] = None,
) -> Tuple[str, str, datetime]:
    """Возвращает (encoded_jwt, jti, expires_at).

    `jti` можно передать снаружи, если нужно сначала выпустить токен, а
    потом записать сессию по тому же jti (или наоборот). Если не задан —
    генерируется здесь.
    """
    auth_data = get_auth_data()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=auth_data['refresh_token_expire_days']
        )
    if jti is None:
        jti = str(uuid4())
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "jti": jti,
    }
    if additional_claims:
        to_encode.update(additional_claims)
    token = jwt.encode(to_encode, auth_data['secret_key'], algorithm=auth_data['algorithm'])
    return token, jti, expire


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """Валидирует JWT-подпись и type='refresh'. НЕ проверяет отзыв —
    это делает вызывающий по jti в user_sessions."""
    auth_data = get_auth_data()
    try:
        decoded = jwt.decode(
            token,
            auth_data['secret_key'],
            algorithms=[auth_data['algorithm']],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    if not decoded.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    return decoded


def extract_client_metadata(request: Optional[Request]) -> Dict[str, Any]:
    """Достаёт IP + User-Agent из FastAPI Request. Не падает, если request
    отсутствует (например, unit-тесты)."""
    if request is None:
        return {"ip_address": None, "user_agent": None}
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    else:
        ip = None
    ua = request.headers.get("user-agent")
    if ua and len(ua) > 512:
        ua = ua[:512]
    return {"ip_address": ip, "user_agent": ua}


async def issue_session_pair(
    session: AsyncSession,
    user: User,
    *,
    request: Optional[Request] = None,
) -> Tuple[str, str]:
    """Создаёт запись user_sessions + возвращает (access_token, refresh_token).

    Используется на /login и в rotate-ветке /refresh.
    """
    meta = extract_client_metadata(request)
    refresh_token, jti, expires_at = create_refresh_token(user.name)
    await user_session_dao.create_user_session(
        session,
        user_id=user.id,
        refresh_jti=jti,
        expires_at=expires_at,
        ip_address=meta["ip_address"],
        user_agent=meta["user_agent"],
    )
    access_token = create_access_token(user.name)
    return access_token, refresh_token


async def rotate_session_pair(
    session: AsyncSession,
    user: User,
    old_session_row: UserSession,
    *,
    request: Optional[Request] = None,
) -> Tuple[str, str]:
    """Отзывает старую сессию и выпускает новую пару. Атомарности между
    revoke и create не требуется — оба под одним sql-соединением, при
    сбое клиент получит 500 и повторит логин."""
    await user_session_dao.revoke_user_session(session, old_session_row)
    return await issue_session_pair(session, user, request=request)


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
