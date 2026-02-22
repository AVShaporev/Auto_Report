from typing import List
from datetime import datetime

from fastapi import APIRouter, Response, Request, Depends, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from service.user import (get_all,
                            get_one,
                            create,
                            modify,
                            delete_by_name,
                            delete_by_id)

from model.user import User
from schema.user import UserResponse, UserRequest
from model.role import Role

from schema.user import UserResponse

from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/api/user', tags=['API'])

@router.get('/list', response_model=List[UserResponse])
async def get_all_users(request: Request, user_auth: User = Depends(get_current_user)):
    
    if not user_auth:
        return None
    
    if not user_auth.role.user_read:
        return None
    users = await get_all()
    
    # FastAPI автоматически преобразует в список схем
    return users

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