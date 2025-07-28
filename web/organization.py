from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from service.organization import (get_one,
                                    get_all,
                                    create,
                                    delete,
                                    modify)
from service.spec_job_title import get_all as get_all_spec_job_titles
from service.bank import get_all as get_all_banks
from service.region import get_all as get_all_regions
from service.arial import get_all as get_all_arials
from service.locality import get_all as get_all_localitys
from service.street import get_all as get_all_streets
from service.spec_build import get_all as get_all_spec_builds
from service.spec_room import get_all as get_all_spec_rooms
from service.contract import (get_by_customer,
                                get_by_executor)

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
    spec_job_titles = await get_all_spec_job_titles()
    banks = await get_all_banks()
    regions = await get_all_regions()
    arials = await get_all_arials()
    localitys = await get_all_localitys()
    streets = await get_all_streets()
    spec_builds = await get_all_spec_builds()
    spec_rooms = await get_all_spec_rooms()
    return templates.TemplateResponse(
        name='organization/create.html', 
        context={
            'request': request,
            'spec_job_titles': spec_job_titles,
            'banks': banks,
            'arials': arials,
            'regions': regions,
            'localitys': localitys,
            'streets': streets,
            'spec_builds': spec_builds,
            'spec_rooms': spec_rooms,
            'user': user})

@router.post('/create')
async def post_create_organization(request: Request,
                        name: str = Form(),
                        short_name: str = Form(),
                        inn: str = Form(),
                        kpp: str = Form(),
                        director_first_name: str = Form(),
                        drector_last_name: str = Form(),
                        drector_surname: str = Form(),
                        email: str = Form(),
                        telephone: str = Form(),
                        site: str = Form(),
                        corr_check: str = Form(),
                        acc_check: str = Form(),
                        pers_check: str = Form(),
                        build_number: str = Form(),
                        room_number: str = Form(),
                        customer: bool = Form(False),
                        executor: bool = Form(False),
                        postal_code: str = Form(),
                        bank_id: int = Form(),
                        region_id: int = Form(),
                        arial_id: int = Form(),
                        locality_id: int = Form(),
                        street_id: int = Form(),
                        spec_build_id: int = Form(),
                        spec_room_id: int = Form(),
                        spec_job_title_id: int = Form(),
                        user: User = Depends(get_current_user)):
    error_msg = None
    organization = Organization(name=name,
                        short_name=short_name,
                        inn=inn,
                        kpp=kpp,
                        director_first_name=director_first_name,
                        drector_last_name=drector_last_name,
                        drector_surname=drector_surname,
                        email=email,
                        telephone=telephone,
                        site=site,
                        corr_check=corr_check,
                        acc_check=acc_check,
                        pers_check=pers_check,
                        build_number=build_number,
                        room_number=room_number,
                        customer=customer,
                        executor=executor,
                        postal_code=postal_code,
                        bank_id=bank_id,
                        region_id=region_id,
                        arial_id=arial_id,
                        locality_id=locality_id,
                        street_id=street_id,
                        spec_build_id=spec_build_id,
                        spec_room_id=spec_room_id,
                        spec_job_title_id=spec_job_title_id)
    try:
        await create(organization = organization)
        organizations = await get_all()
        create_ok = True
        return RedirectResponse(url=f"{organization.id}", status_code=303)
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

@router.get('/{organization_id}/edit')
async def get_modify_organization(request: Request,
                                    organization_id: str = '',
                                    user: User = Depends(get_current_user)):
    organization = await get_one(int(organization_id))
    return templates.TemplateResponse(
        name='organization/info.html',
        context={'request': request,
                'organization': organization})

@router.get('/{organization_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    organization_id: str = ''):
    organization = await get_one(int(organization_id))
    customer_contracts = await get_by_customer(int(organization_id))
    executor_contracts = await get_by_executor(int(organization_id))
    contracts = customer_contracts + executor_contracts
    return templates.TemplateResponse(
        name='organization/info.html',
        context={'request': request,
                'organization': organization,
                'contracts': contracts})



@router.get("/link/external_link")
async def get_external_link(link: str = "https://www.example.com"):  # Здесь link - это параметр с типом str и значением по умолчанию
    return {"external_link": link}