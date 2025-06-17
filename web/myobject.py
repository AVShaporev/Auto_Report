from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.object import (get_one,
                                    get_all,
                                    create,
                                    delete,
                                    modify)
from model.object import Object
from model.user import User
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/object', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_objects_html(request: Request, user: User = Depends(get_current_user)):
    myobjects = await get_all()
    return templates.TemplateResponse(
        name='object/list.html', 
        context={
            'request': request,
            'objects': myobjects, 
            'user': user})

@router.get('/{object_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    object_id: str = ''):
    myobject = await get_one(int(object_id))
    return templates.TemplateResponse(
        name='object/info.html',
        context={'request': request,
                'object': myobject})