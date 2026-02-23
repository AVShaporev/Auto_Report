from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Response, Request, Depends, Form, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse

from service.user import (get_all,
                            get_one,
                            create,
                            modify,
                            delete_by_name,
                            delete_by_id,
                            get_users_paginated)

from model.user import User

from service.auth import (get_current_user)

from schema.user import UserResponse, UserRequest
from schema.pagination import PaginationParams, PaginatedResponse

from model.role import Role

from errors import Duplicate, Missing, BaseLocking


router = APIRouter(prefix='/api/user', tags=['API'])

# @router.get('/list', response_model=List[UserResponse])
# async def get_all_users(request: Request, user_auth: User = Depends(get_current_user)):
    
#     if not user_auth:
#         return None
    
#     if not user_auth.role.user_read:
#         return None
#     users = await get_all()
    
#     # FastAPI автоматически преобразует в список схем
#     return users

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
        print(f'{user_auth.role.user_create=}')
        if user_auth.role.user_create:
            try:
                user = await create(user_create = user)
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

@router.put('/{user_id}')
async def put_modify_user(
                            user_id: int,
                            user: UserResponse,
                            user_auth: User = Depends(get_current_user)
                            ):

    error_msg = None
    user = UserResponse(
                        )
    
    if user_auth:
        if user_auth.role.role_modify:
            try:
                user = await modify(user_id = user_id, user = user)
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