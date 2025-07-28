from datetime import datetime

from fastapi import APIRouter, Response, Request, Depends, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from service.spec_job_title import (create,
                                    get_all)

from model.spec_job_title import Spec_Job_Title
from model.user import User

from schema.spec_job_title import SpecJobTitleResponse

from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/api/spec_job_title', tags=['API'])
templates = Jinja2Templates(directory='templates')

@router.get('/list')
async def get_spec_job_titles_html(request: Request, user: User = Depends(get_current_user)):
    spec_job_titles = await get_all()
    return spec_job_titles

@router.post('/create')
async def post_create_spec_job_title(spec_job_title: SpecJobTitleResponse):
    error_msg = None
    spec_job_title = Spec_Job_Title(name=spec_job_title.name,
                                    description=spec_job_title.description)
    try:
        spec_job_title = await create(spec_job_title = spec_job_title)
        spec_job_titles = await get_all()
        create_ok = True
        return JSONResponse({"id": spec_job_title.id, "name": spec_job_title.name})

    except Duplicate:
        error_msg = "Должность с таким именем уже существует!"
        spec_job_titles = get_all()
        return False

    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        spec_job_titles = get_all()
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