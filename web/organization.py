from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.organization import get_one, get_all, create, delete, modify
from model.organization import Organization
from model.user import User
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)


router = APIRouter(prefix='/organization', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_explorers_html(request: Request, user: User = Depends(get_current_user)):
    organizations = await get_all()
    return templates.TemplateResponse(
        name='organization/list.html', 
        context={
            'request': request,
            'organizations': organizations, 
            'user': user})

@router.post('/create')
async def create_explorer(request: Request,
                        name: str = Form(),
                        country: str = Form(),
                        description: str = Form(),
                        user: User = Depends(get_current_user)):
    error_msg = None
    explorer = Explorer(name=name,
                    description=description,
                    country=country)
    try:
        await create(explorer = explorer)
        explorers = await get_all()
        create_ok = True
        return templates.TemplateResponse(
            name='explorer/list.html', 
            context={
                'request': request,
                'explorer': explorer,
                'explorers': explorers,
                'create_ok': create_ok, 
                'user': user})
    except Duplicate:
        error_msg = "Исследователь с таким именем уже существует!"
        explorers = get_all()
        return templates.TemplateResponse(
            name='explorer/create.html', 
            context={
                'request': request,
                'explorer': explorer,
                'error_msg': duplicate})
    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        explorers = get_all()
        return templates.TemplateResponse(
            name='explorer/create.html', 
            context={
                'request': request,
                'explorer': explorer,
                'error_msg': duplicate})