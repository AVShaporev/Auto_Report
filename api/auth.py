from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from jose import jwt
from jose.exceptions import JWTError

from config import get_db_url as get_db, get_auth_data
from service import auth as security
from config import settings
from schema import token as token_schema
from schema.user import UserBase, LoginResponse, UserLogin

from service.auth import (create_access_token,
                            authenticate_user,
                            get_current_user)

from model.user import User
from model.dao import UsersDAO


class RefreshRequest(BaseModel):
    refresh_token: str


router = APIRouter(prefix='/api/auth', tags=['API'])

@router.post("/login", response_model=LoginResponse)
async def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):

    user = await authenticate_user(
        form_data.username, form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = security.create_access_token(user.name)
    refresh_token = security.create_refresh_token(user.name)
    
    user = UserLogin.model_validate(user)

    response_auth_user = LoginResponse(user=user,
                                        access_token=access_token,
                                        refresh_token=refresh_token)

    return response_auth_user

@router.post("/refresh", response_model=token_schema.Token)
async def refresh_token(payload: RefreshRequest):
    auth_data = get_auth_data()
    try:
        decoded = jwt.decode(
            payload.refresh_token,
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

    username = decoded.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = await UsersDAO.find_one_or_none(name=username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access_token = security.create_access_token(username)
    return {
        "username": username,
        "access_token": new_access_token,
        "refresh_token": payload.refresh_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserLogin)
async def login(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return user