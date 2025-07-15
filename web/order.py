from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.order import (get_one,
                            get_all,
                            create,
                            delete,
                            modify)
from model.order import Order
from model.user import User
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/order', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_order_html(request: Request, user: User = Depends(get_current_user)):
    orders = await get_all()
    return templates.TemplateResponse(
        name='order/list.html', 
        context={
            'request': request,
            'orders': orders, 
            'user': user})

@router.get('/{order_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    order_id: str = ''):
    order = await get_one(int(order_id))
    return templates.TemplateResponse(
        name='order/info.html',
        context={'request': request,
                'order': order})