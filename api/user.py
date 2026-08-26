from typing import List, Optional
from datetime import datetime

from fastapi import (
                        APIRouter,
                        Response,
                        Request,
                        Depends,
                        Form,
                        Query,
                        HTTPException,
                        status,
                    )
from fastapi.responses import (
                                HTMLResponse,
                                JSONResponse
                                )
from pydantic import BaseModel, ConfigDict, Field

from service.user import (get_all,
                            get_one,
                            create,
                            modify,
                            delete_by_id,
                            get_users_paginated)

from model.user import User

from service.auth import (get_current_user)
from database.database import new_session
from data import user_session as user_session_dao
from data import push_token as push_token_dao

from schema.user import UserResponse, UserRequest, UserUpdate
from schema.pagination import PaginationParams, PaginatedResponse

from model.role import Role

from errors import Duplicate, Missing, BaseLocking


async def _assert_can_assign_role(role_id: Optional[int], caller: User) -> None:
    """Разрешаем назначить superadmin-роль только другому superadmin'у.

    Обычный админ (user_create/user_modify + is_admin) может создавать/менять
    юзеров, но НЕ имеет права выставить им role_id, ссылающийся на роль с
    is_superadmin=True. Без этой проверки любой админ мог бы поднять права
    себе или коллеге до полного superadmin.
    """
    if role_id is None:
        return
    if caller and getattr(caller.role, "is_superadmin", False):
        return
    async with new_session() as session:
        target_role = await session.get(Role, role_id)
    if target_role is not None and target_role.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль «superadmin» может назначить только суперадминистратор.",
        )


_ALLOWED_PLATFORMS = {"ios", "android", "web"}


class PushTokenRegisterRequest(BaseModel):
    platform: str = Field(..., description="ios / android / web")
    token: str = Field(..., min_length=8, max_length=512)
    device_id: Optional[str] = Field(None, max_length=128)
    app_version: Optional[str] = Field(None, max_length=32)


class PushTokenDeleteRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=512)


class PushTokenResponse(BaseModel):
    id: int
    platform: str
    token: str
    device_id: Optional[str] = None
    app_version: Optional[str] = None
    last_seen_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix='/api/user', tags=['API'])


@router.post("/me/push-token", response_model=PushTokenResponse)
async def register_push_token(
    payload: PushTokenRegisterRequest,
    current_user: User = Depends(get_current_user),
):
    """Регистрация FCM/APNs токена текущего юзера. Upsert по `token`
    (если этот же токен уже был зарегистрирован — на другого юзера,
    например при смене логина на устройстве — user_id перезаписывается)."""
    if payload.platform not in _ALLOWED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"platform must be one of {sorted(_ALLOWED_PLATFORMS)}",
        )
    async with new_session() as session:
        row = await push_token_dao.upsert_push_token(
            session,
            user_id=current_user.id,
            platform=payload.platform,
            token=payload.token,
            device_id=payload.device_id,
            app_version=payload.app_version,
        )
    return PushTokenResponse.model_validate(row)


@router.delete("/me/push-token", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_push_token(
    payload: PushTokenDeleteRequest,
    current_user: User = Depends(get_current_user),
):
    """Клиент разлогинивается или отзывает разрешение push — сносим
    его регистрацию по token."""
    async with new_session() as session:
        await push_token_dao.delete_push_token(
            session, current_user.id, payload.token
        )


@router.get("/me/push-tokens", response_model=List[PushTokenResponse])
async def list_my_push_tokens(
    current_user: User = Depends(get_current_user),
):
    async with new_session() as session:
        rows = await push_token_dao.list_push_tokens_for_user(
            session, current_user.id
        )
    return [PushTokenResponse.model_validate(r) for r in rows]

@router.get("/list", response_model=PaginatedResponse[UserResponse])
async def get_users(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск"),
    role_id: Optional[int] = Query(None, ge=1, description="Фильтр по роли"),
    is_active: Optional[bool] = Query(None, description="Только активные"),
    sort_by: str = Query("id", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список пользователей с пагинацией
    """
    # Проверка прав
    if not current_user.role.user_read:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Получаем данные
    users, total = await get_users_paginated(
        pagination=pagination,
        search=search,
        role_id=role_id,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Формируем ответ
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=users,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages
    )

@router.post('/create')
async def post_create_user(
                            request: Request,
                            user: UserRequest,
                            user_auth: User = Depends(get_current_user)
                            ):
    error_msg = None
    if user_auth:
        if user_auth.role.user_create:
            await _assert_can_assign_role(user.role_id, user_auth)
            try:
                user_name_for_log = user.name
                user = await create(user_create = user)
                from service.activity_log import log_activity
                async with new_session() as _s:
                    await log_activity(
                        _s, user_auth,
                        action='create', entity='user', entity_id=None,
                        summary=f'Создал пользователя «{user_name_for_log}»',
                    )
                create_ok = True
                return create_ok

            except Duplicate:
                error_msg = "Пользователь с таким именем уже существует!"
                users = get_all()
                return False

            except BaseLocking:
                error_msg = "База данных недоступна для записи!"
                users = get_all()
                return False
        return None
# 
@router.delete('/{user_id}')
async def delete(request: Request, user: User = Depends(get_current_user), user_id: int = None):
    if user:
        if user.role.user_delete:
            try:
                res = await delete_by_id(user_id)
                if res:
                    from service.activity_log import log_activity
                    async with new_session() as _s:
                        await log_activity(
                            _s, user,
                            action='delete', entity='user', entity_id=user_id,
                            summary=f'Удалил пользователя (id={user_id})',
                        )
                return res
            except BaseLocking:
                error_msg = "База данных недоступна для записи!"
                users = await get_all()
                return False
        else:
            raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У Вас недостаточно прав для удаления ролей"
            )
    else:
        raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="У Вас недостаточно прав для удаления ролей"
        )
    return None

@router.post('/{user_id}/revoke-all-sessions')
async def revoke_all_sessions(
    user_id: int,
    user_auth: User = Depends(get_current_user),
):
    """Админ-эндпоинт: разлогинить юзера со всех устройств. Помечает
    revoked_at у всех активных user_sessions выбранного юзера."""
    if not (user_auth and user_auth.role.user_modify):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )
    async with new_session() as session:
        revoked = await user_session_dao.revoke_all_user_sessions(session, user_id)
    return {"revoked": revoked}


@router.put('/{user_id}')
async def put_modify_user(
                            user_id: int,
                            user: UserUpdate,
                            user_auth: User = Depends(get_current_user)
                            ):
    # Раньше здесь был `user = UserUpdate()` — это стирало тело запроса
    # (клиентские данные терялись, в сервис уходил пустой объект). Убрано.
    error_msg = None

    if user_auth:
        # Раньше тут стояло `role.role_modify` — копипаста из эндпоинтов ролей.
        # Для user-эндпоинта корректный флаг — `role.user_modify`.
        if user_auth.role.user_modify:
            await _assert_can_assign_role(user.role_id, user_auth)
            try:
                update_data_dump = user.model_dump(exclude_unset=True)
                user = await modify(user_id = user_id, user = user)
                from service.activity_log import log_activity
                async with new_session() as _s:
                    await log_activity(
                        _s, user_auth,
                        action='update', entity='user', entity_id=user.id,
                        summary=f'Изменил пользователя «{user.name}»',
                        details=update_data_dump,
                    )
                modify_ok = True
                return JSONResponse({"id": user.id,
                                    "name": user.name})

            except Duplicate:
                error_msg = "Пользователь с таким именем уже существует!"
                users = get_all()
                return False

            except BaseLocking:
                error_msg = "База данных недоступна для записи!"
                users = get_all()
                return False
        return None