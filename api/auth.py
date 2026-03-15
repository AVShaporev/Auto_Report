from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from config import get_db_url as get_db
from service import auth as security
from config import settings
from service import user as crud_user
from schema import token as token_schema
from schema.user import UserBase, LoginResponse, UserLogin

from service.auth import (create_access_token,
                            authenticate_user,
                            get_current_user)

from model.user import User


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
            detail="Incorrect username or password",
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
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    payload = security.verify_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    username = payload.get("sub")
    user = crud_user.get_user_by_username(db, username=username)
    
    # Проверяем, что токен валидный и не был отозван
    if not user or user.refresh_token != refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    new_access_token = security.create_access_token(user.username)
    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserLogin)
async def login(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return user