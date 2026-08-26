from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict

from database.database import new_session
from schema import token as token_schema
from schema.user import UserLogin, LoginResponse

from service.auth import (
    authenticate_user,
    create_access_token,
    decode_refresh_token,
    get_current_user,
    issue_session_pair,
    rotate_session_pair,
)

from model.user import User
from model.dao import UsersDAO
from data import user_session as user_session_dao


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class MobileOnboardRequest(BaseModel):
    token: str


class SessionResponse(BaseModel):
    id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    geo_country: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix='/api/auth', tags=['API'])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with new_session() as session:
        access_token, refresh_token = await issue_session_pair(
            session, user, request=request
        )
        from service.activity_log import log_activity
        await log_activity(
            session, user,
            action='login', entity='auth', entity_id=user.id,
            summary=f'{user.name} вошёл в систему',
        )

    user_out = UserLogin.model_validate(user)
    return LoginResponse(
        user=user_out,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=token_schema.Token)
async def refresh_token(payload: RefreshRequest, request: Request):
    decoded = decode_refresh_token(payload.refresh_token)
    username = decoded["sub"]
    jti = decoded.get("jti")

    user = await UsersDAO.find_one_or_none(name=username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    async with new_session() as session:
        session_row = None
        if jti:
            session_row = await user_session_dao.get_user_session_by_jti(session, jti)

        if session_row is None:
            # Legacy fallback: старый токен без записи в user_sessions.
            # Web-клиент продолжает работать до истечения. Не ротируем —
            # выдаём только новый access, тот же refresh.
            new_access = create_access_token(username)
            return {
                "username": username,
                "access_token": new_access,
                "refresh_token": payload.refresh_token,
                "token_type": "bearer",
            }

        if session_row.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session revoked",
            )
        exp = session_row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired",
            )
        if session_row.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session user mismatch",
            )

        access_token, new_refresh = await rotate_session_pair(
            session, user, session_row, request=request
        )

    return {
        "username": username,
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
):
    """Revoke текущей сессии. Клиент передаёт свой refresh_token в теле —
    по jti находим сессию и помечаем revoked."""
    if not payload.refresh_token:
        # Пустое тело — no-op success, всё равно клиент дропнет токены локально.
        return
    try:
        decoded = decode_refresh_token(payload.refresh_token)
    except HTTPException:
        return
    jti = decoded.get("jti")
    if not jti:
        return
    async with new_session() as session:
        row = await user_session_dao.get_user_session_by_jti(session, jti)
        if row and row.user_id == current_user.id:
            await user_session_dao.revoke_user_session(session, row)
            from service.activity_log import log_activity
            await log_activity(
                session, current_user,
                action='logout', entity='auth', entity_id=current_user.id,
                summary=f'{current_user.name} вышел из системы',
            )


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Список активных сессий текущего юзера. Не помечает current —
    у access-токена нет jti; клиент сам сопоставит по своему сохранённому
    refresh если нужно."""
    async with new_session() as session:
        rows = await user_session_dao.list_user_sessions_for_user(
            session, current_user.id, active_only=True
        )
    return [SessionResponse.model_validate(r) for r in rows]


@router.post("/sessions/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
):
    async with new_session() as session:
        row = await user_session_dao.get_user_session_by_id(session, session_id)
        if row is None or row.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        await user_session_dao.revoke_user_session(session, row)


@router.post("/mobile-onboard", response_model=LoginResponse)
async def mobile_onboard(
    payload: MobileOnboardRequest,
    request: Request,
):
    """Обменять master-выпущенный onboard-JWT на пару (access, refresh) без пароля.

    Master (POST /api/tenants/{slug}/mobile-onboard-token) подписывает
    JWT: {sub: username, tenant: slug, type: 'mobile_onboard', iat, exp, nonce}
    ключом MOBILE_ONBOARD_SECRET. Здесь мы валидируем тем же ключом,
    проверяем tenant = TENANT_SLUG (мы уверены, что это наш tenant, не
    подмешали чужой onboard), находим юзера и вызываем issue_session_pair —
    получается обычная пара (access, refresh) через существующий M1.1 flow.
    """
    from jose import jwt
    from jose.exceptions import JWTError
    from config import settings
    from service.auth import issue_session_pair as _issue

    if not settings.MOBILE_ONBOARD_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile onboarding disabled: MOBILE_ONBOARD_SECRET не задан.",
        )

    try:
        decoded = jwt.decode(
            payload.token,
            settings.MOBILE_ONBOARD_SECRET,
            algorithms=["HS256"],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired onboard token",
        )

    if decoded.get("type") != "mobile_onboard":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    token_tenant = decoded.get("tenant")
    if settings.TENANT_SLUG and token_tenant != settings.TENANT_SLUG:
        # Токен выпущен для другого tenant'а — отдаём 401 (не 403, чтобы
        # клиент понял: неверный tenant, надо переспросить нужный slug).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token issued for different tenant",
        )

    username = decoded.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub",
        )

    user = await UsersDAO.find_with_role(name=username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    async with new_session() as session:
        access_token, refresh_token = await _issue(session, user, request=request)

    user_out = UserLogin.model_validate(user)
    return LoginResponse(
        user=user_out,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=UserLogin)
async def me(
    user: User = Depends(get_current_user),
):
    return user
