from fastapi import APIRouter, Request, Depends, Form, Depends
from fastapi.templating import Jinja2Templates

from service.report import (get_one,
                            get_all,
                            create,
                            delete,
                            modify)
from model.report import Report
from model.user import User
from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/report', tags=['Фронтенд'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_reports_html(request: Request, user: User = Depends(get_current_user)):
    reports = await get_all()
    return templates.TemplateResponse(
        name='report/list.html', 
        context={
            'request': request,
            'reports': reports, 
            'user': user})

@router.get('/{report_id}')
async def get_one_web(request: Request,
                    user: User = Depends(get_current_user),
                    report_id: str = ''):
    report = await get_one(int(report_id))
    return templates.TemplateResponse(
        name='report/info.html',
        context={'request': request,
                'report': report})