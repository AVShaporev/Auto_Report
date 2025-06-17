from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.sub_contract import (get_one,
                                    get_all,
                                    create,
                                    delete,
                                    modify)
from model.sub_contract import Sub_Contract
from model.user import User
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/sub_contract', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_contracts_html(request: Request, user: User = Depends(get_current_user)):
    sub_contracts = await get_all()
    return templates.TemplateResponse(
        name='sub_contract/list.html', 
        context={
            'request': request,
            'sub_contracts': sub_contracts, 
            'user': user})

@router.get('/{sub_contracts_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    sub_contract_id: str = ''):
    sub_contract = await get_one(int(sub_contract_id))
    return templates.TemplateResponse(
        name='sub_contract/info.html',
        context={'request': request,
                'sub_contract': sub_contracts})