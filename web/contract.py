from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from service.contract import (get_one,
                                    get_all,
                                    create,
                                    delete,
                                    modify)
from service.spec_contract import get_all as get_all_spec_contracts
from service.organization import get_all_customers
from service.organization import get_all_executors

from model.contract import Contract
from model.user import User

from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/contract', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_contracts_html(request: Request, user: User = Depends(get_current_user)):
    contracts = await get_all()
    return templates.TemplateResponse(
        name='contract/list.html', 
        context={
            'request': request,
            'contracts': contracts, 
            'user': user})

@router.get('/create')
async def get_create_contract(request: Request,
                        user: User = Depends(get_current_user)):
    spec_contracts = await get_all_spec_contracts()
    customers = await get_all_customers()
    executors = await get_all_executors()
    return templates.TemplateResponse(name='contract/create.html', 
                                        context={
                                            'request': request,
                                            'spec_contracts': spec_contracts,
                                            'customers': customers,
                                            'executors': executors,
                                            'user': user})

@router.post('/create')
async def post_create_contract(request: Request,
                        spec_contract: int = Form(),
                        number: str = Form(),
                        date_of_consclusion: str = Form(),
                        date_of_completion: str = Form(),
                        summ: float = Form(),
                        subject: str = Form(),
                        short_subject: str = Form(),
                        type_contract: str = Form(),
                        customer_id: int = Form(),
                        executor_id: int = Form(),
                        description: str = Form(),
                        user: User = Depends(get_current_user)):
    error_msg = None
    contract = Contract(spec_contract_id=spec_contract,
                        number=number, 
                        date_of_consclusion=datetime.strptime(date_of_consclusion, "%d.%m.%Y").date(),
                        date_of_completion=datetime.strptime(date_of_completion, "%d.%m.%Y").date(),
                        summ=float(summ),
                        subject=subject,
                        short_subject=short_subject,
                        type_contract=type_contract,
                        customer_id=customer_id, 
                        executor_id=executor_id,
                        description=description)
    try:
        await create(contract = contract)
        contracts = await get_all()
        create_ok = True
        return RedirectResponse(url=f"{contract.id}", status_code=303)

    except Duplicate:
        error_msg = "Контракт с таким номером уже существует!"
        contracts = get_all()
        return templates.TemplateResponse(name='contract/create.html', 
                                        context={
                                            'request': request,
                                            'spec_contracts': spec_contracts,
                                            'customers': customers,
                                            'executors': executors,
                                            'user': user})
    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        contracts = get_all()
        return templates.TemplateResponse(name='contract/create.html', 
                                        context={
                                            'request': request,
                                            'spec_contracts': spec_contracts,
                                            'customers': customers,
                                            'executors': executors,
                                            'user': user})

@router.get('/{contract_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    contract_id: str = ''):
    contract = await get_one(int(contract_id))
    return templates.TemplateResponse(
        name='contract/info.html',
        context={'request': request,
                'contract': contract})