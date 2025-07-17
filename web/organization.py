from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.organization import (get_one,
                                    get_all,
                                    create,
                                    delete,
                                    modify)
from model.organization import Organization
from model.user import User
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)


router = APIRouter(prefix='/organization', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_organizations_html(request: Request, user: User = Depends(get_current_user)):
    organizations = await get_all()
    return templates.TemplateResponse(
        name='organization/list.html', 
        context={
            'request': request,
            'organizations': organizations, 
            'user': user})


@router.get('/create')
async def get_create_organization(request: Request,
                        user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        name='organization/create.html', 
        context={
            'request': request,
            'user': user})

@router.post('/create')
async def create_organization(request: Request,
                        name: str = Form(),
                        country: str = Form(),
                        description: str = Form(),
                        user: User = Depends(get_current_user)):
    error_msg = None
    organization = Organization(name=name,
                    description=description,
                    country=country)
    try:
        await create(organization = organization)
        organizations = await get_all()
        create_ok = True
        return templates.TemplateResponse(name='organization/list.html', 
                                            context={
                                                'request': request,
                                                'organization': organization,
                                                'organizations': organizations,
                                                'create_ok': create_ok, 
                                                'user': user})
    except Duplicate:
        error_msg = "Организация с таким наименованием уже существует!"
        organizations = get_all()
        return templates.TemplateResponse(name='organization/create.html', 
                                            context={
                                                'request': request,
                                                'organization': organization,
                                                'error_msg': duplicate})
    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        organizations = get_all()
        return templates.TemplateResponse(name='organization/create.html', 
                                            context={
                                                'request': request,
                                                'organization': organization,
                                                'error_msg': duplicate})

@router.get('/{organization_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    organization_id: str = ''):
    organization = await get_one(int(organization_id))
    return templates.TemplateResponse(
        name='organization/info.html',
        context={'request': request,
                'organization': organization})


@router.get("/link/external_link")
async def get_external_link(link: str = "https://www.example.com"):  # Здесь link - это параметр с типом str и значением по умолчанию
    return {"external_link": link}