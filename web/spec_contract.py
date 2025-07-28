from datetime import datetime

from fastapi import APIRouter, Response, Request, Depends, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# from service.contract import (get_one,
#                                     get_all,
#                                     create,
#                                     delete,
#                                     modify)
from service.spec_contract import (create,
                                    get_all)
# from service.organization import get_all_customers
# from service.organization import get_all_executors

from model.spec_contract import Spec_Contract
from model.user import User

from schema.spec_contract import SpecContractResponse

from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/spec_contract', tags=['Фротенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_contracts_html(request: Request, user: User = Depends(get_current_user)):
    spec_contracts = await get_all()
    return spec_contracts

# @router.get('/create')
# async def get_create_spec_contract(request: Request,
#                         user: User = Depends(get_current_user)):
#     spec_contracts = await get_all_spec_contracts()
#     customers = await get_all_customers()
#     executors = await get_all_executors()
#     return templates.TemplateResponse(name='contract/create.html', 
#                                         context={
#                                             'request': request,
#                                             'spec_contracts': spec_contracts,
#                                             'customers': customers,
#                                             'executors': executors,
#                                             'user': user})

@router.post('/create')
async def post_create_spec_contract(spec_contract: SpecContractResponse):
    print(spec_contract.name, spec_contract.description)
    error_msg = None
    spec_contract = Spec_Contract(name=spec_contract.name,
                                    description=spec_contract.description)
    try:
        spec_contract = await create(spec_contract = spec_contract)
        spec_contracts = await get_all()
        create_ok = True
        return JSONResponse({"id": spec_contract.id, "name": spec_contract.name})

    except Duplicate:
        error_msg = "Контракт с таким номером уже существует!"
        contracts = get_all()
        return False

    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        contracts = get_all()
        return False

# @router.get('/{contract_id}')
# async def get_one_web(request: Request,
#                     user: User = Depends(get_current_user),
#                     contract_id: str = ''):
#     contract = await get_one(int(contract_id))
#     return templates.TemplateResponse(
#         name='contract/info.html',
#         context={'request': request,
#                 'contract': contract})