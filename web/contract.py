from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.contract import (get_one,
                                    get_all,
                                    create,
                                    delete,
                                    modify)
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

@router.get('/{contract_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    contract_id: str = ''):
    contract = await get_one(int(contract_id))
    return templates.TemplateResponse(
        name='contract/info.html',
        context={'request': request,
                'contract': contract})