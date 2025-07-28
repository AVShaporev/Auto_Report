from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.locality import (get_one,
                                    get_all,
                                    create,
                                    delete,
                                    modify)
from service.spec_locality import get_all as get_all_spec_localitys

from model.locality import Locality
from model.user import User
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/locality', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_locality_html(request: Request, user: User = Depends(get_current_user)):
    localitys = await get_all()
    return templates.TemplateResponse(
        name='locality/list.html', 
        context={
            'request': request,
            'localitys': localitys, 
            'user': user})

@router.get('/create')
async def get_create_locality(request: Request,
                        user: User = Depends(get_current_user)):
    # if user is None:
    #     return templates.TemplateResponse(name='index.html',
    #                                         context={'request': request, 
    #                                                     'user': user})

    spec_localitys = await get_all_spec_localitys()

    return templates.TemplateResponse(name='locality/create.html',
                                            context={'request': request, 
                                                        'user': user,
                                                        'spec_localitys': spec_localitys})

@router.post('/create')
async def post_create_locality(request: Request,
                                name: str = Form(),
                                spec_locality_id: int = Form(),
                                description: str = Form(),
                                user: User = Depends(get_current_user)):
    locality = Locality(name=name,
                        spec_locallity_id=spec_locality_id,
                        description=description)

    # if user is None:
    #     return templates.TemplateResponse(name='main.html',
    #                                         context={'request': request, 
    #                                                     'user': user})
    
    # if user.name in ('superadmin', 'admin'):
    #     mod_flag = True
    #     create_flag = True
    
    # if user.name == 'superadmin':
    #     del_flag = True

    error_msg = None
    try:
        create_ok = await create(locality)
        localitys = await get_all()
        return templates.TemplateResponse(name='locality/list.html',
                                        context={'request': request,
                                                    'localitys':localitys})
    except Duplicate:
        error_msg = "Населённый пункт с таким именем уже существует!"
        localitys = get_all()
        return templates.TemplateResponse(
            name='locality/list.html', 
            context={
                'request': request,
                'localitys':localitys})
    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        localitys = get_all()
        return templates.TemplateResponse(
            name='locality/list.html', 
            context={
                'request': request,
                'localitys':localitys})

@router.get('/{locality_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    locality_id: str = ''):
    locality = await get_one(int(locality_id))
    return templates.TemplateResponse(
        name='locality/info.html',
        context={'request': request,
                'locality': locality})