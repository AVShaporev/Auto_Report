import requests

from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.equipment import (get_one,
                                get_all,
                                create,
                                delete,
                                modify)
from model.equipment import Equipment
from model.user import User
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/equipment', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_objects_html(request: Request, user: User = Depends(get_current_user)):
    equipments = await get_all()
    return templates.TemplateResponse(
        name='equipment/list.html', 
        context={
            'request': request,
            'equipments': equipments, 
            'user': user})

@router.get('/{equipment_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    equipment_id: str = ''):
    equipment = await get_one(int(equipment_id))
    url_for_google = requests.get('https://www.google.com/search', {'q': equipment.name}).url
    return templates.TemplateResponse(
        name='equipment/info.html',
        context={'request': request,
                'url_for_google': url_for_google,
                'equipment': equipment})