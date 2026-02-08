from typing import Annotated

from fastapi import (APIRouter,
                        Request,
                        Depends,
                        HTTPException,
                        Response,
                        status,
                        Form)
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from model.user import User
from schema.user import SUserAuth
from service.user import (create,
                            get_all,
                            get_one)
from service.role import get_all as get_all_roles
from service.user import get_all as get_all_users

from service.auth import (create_access_token,
                            authenticate_user,
                            get_current_user)

from errors import (Duplicate,
                    BaseLocking)


router = APIRouter(prefix='/user', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

# выполнение входа
@router.post("/login")
async def auth_user(request: Request,
                    response: Response,
                    login: Annotated[str, Form()],
                    password: Annotated[str, Form()]):

    user_data = SUserAuth(login=login, password=password)

    check = await authenticate_user(login=user_data.login, password=user_data.password)

    if check is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Неверная почта или пароль')

    access_token = create_access_token({"sub": str(check[0].id)})

    user = await get_one(user_data.login)

    res = templates.TemplateResponse(name='index.html', request=request, context={'user': user})
    
    res.set_cookie(key="users_access_token", value=access_token)

    return res

@router.get("/logout")
async def logout_user(request: Request, response:Response):
    res = templates.TemplateResponse(name='index.html', context={'request': request})
    res.delete_cookie(key="users_access_token")
    return res


@router.get('/list')
async def get_explorers_html(request: Request,
                                users=Depends(get_all),
                                user: User = Depends(get_current_user)): 

    mod_flag = False
    del_flag = False
    create_flag = False

    if user is None:
        return templates.TemplateResponse(name='main.html',
                                            context={'request': request, 
                                                        'user': user,
                                                        'message': 'Недостаточно прав!'})
    
    if user.name in ('superadmin', 'admin'):
        mod_flag = True
        create_flag = True
    
    if user.name == 'superadmin':
        del_flag = True

    users = await get_all_users()
    print(users)

    return templates.TemplateResponse(name='user/list.html',
                                        context={'request': request,
                                                    'users': users,
                                                    'user': user})

@router.post("/main")
async def get_user_login(request: Request):
    return templates.TemplateResponse(name='main.html',
                                        context={'request': request})

@router.get('/create')
async def get_create_user(request: Request,
                        user: User = Depends(get_current_user)):
    if user is None:
        return templates.TemplateResponse(name='main.html',
                                            context={'request': request, 
                                                        'user': user})

    roles = await get_all_roles()

    return templates.TemplateResponse(name='user/create.html',
                                            context={'request': request, 
                                                        'user': user,
                                                        'roles': roles})

@router.post('/create')
async def create_user(request: Request,
                        name: str = Form(),
                        password: str = Form(),
                        role_id: int = Form(),
                        user: User = Depends(get_current_user)):

    user_name = name
    user_role_id = role_id

    if user is None:
        return templates.TemplateResponse(name='index.html',
                                            context={'request': request, 
                                                        'user': user})

    error_msg = None
    try:
        create_ok = await create(name=name,
                        password=password,
                        role_id=role_id)
        users = await get_all()
        return templates.TemplateResponse(name='user/list.html',
                                        context={'request': request,
                                                    'users': users,
                                                    'user': user})
    except Duplicate:
        error_msg = "Пользователь с таким именем уже существует!"
        users = get_all()
        return templates.TemplateResponse(
            name='user/list.html', 
            context={
                'request': request,
                'user': user,
                'error_msg': error_msg,
                'user_name': user_name,
                'user_role_id': user_role_id})
    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        users = get_all()
        return templates.TemplateResponse(
            name='user/list.html', 
            context={
                'request': request,
                'user': user,
                'error_msg': error_msg,
                'user_name': user_name,
                'user_role_id': user_role_id})