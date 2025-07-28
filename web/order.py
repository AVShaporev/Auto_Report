from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.order import (get_one,
                            get_all,
                            create,
                            delete,
                            modify)
from service.spec_order import get_all as get_all_spec_order
from service.contract import get_all as get_all_contract
from service.object import get_all as get_all_object
from model.order import Order
from model.user import User
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/order', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

# список заявок
@router.get('/list')
async def get_order_html(request: Request, user: User = Depends(get_current_user)):
    orders = await get_all()
    return templates.TemplateResponse(
        name='order/list.html', 
        context={
            'request': request,
            'orders': orders, 
            'user': user})

# получение формы для создания заявки
@router.get('/create')
async def get_create_order(request: Request,
                            user: User = Depends(get_current_user)):
    spec_orders = await get_all_spec_order()
    contracts = await get_all_contract()
    objects = await get_all_object()
    return templates.TemplateResponse(name='order/create.html', 
                                        context={
                                            'request': request,
                                            'spec_orders': spec_orders,
                                            'contracts': contracts,
                                            'objects': objects,
                                            'user': user})

# создание заявки - после заполнения формы создания
@router.post('/create')
async def create_organization(request: Request,
                                spec_order_id: int = Form(),
                                contract_id: int = Form(),
                                object_id: int = Form(),
                                user: User = Depends(get_current_user)):
    error_msg = None
    number = "123"  # d в будущем исправить - придумать номер аналогично актам ТО.
    order = Order(number=number,
                    spec_order_id=spec_order_id,
                    contract_id=contract_id,
                    object_id=object_id,
                    user_id=user.id,
                    report_id=None)
    try:
        await create(order = order)
        orders = await get_all()
        create_ok = True
        return templates.TemplateResponse(name='order/list.html', 
                                            context={
                                                'request': request,
                                                'order': order,
                                                'orders': orders,
                                                'create_ok': create_ok, 
                                                'user': user})
    except Duplicate:
        error_msg = "Заявка с таким номером уже существует!"
        orders = get_all()
        return templates.TemplateResponse(name='order/create.html', 
                                            context={
                                                'request': request,
                                                'order': order,
                                                'error_msg': duplicate})
    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        orders = get_all()
        return templates.TemplateResponse(name='order/create.html', 
                                            context={
                                                'request': request,
                                                'order': order,
                                                'error_msg': duplicate})

@router.get('/{order_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    order_id: str = ''):
    order = await get_one(int(order_id))
    return templates.TemplateResponse(
        name='order/info.html',
        context={'request': request,
                'order': order})