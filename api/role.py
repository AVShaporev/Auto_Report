from datetime import datetime

from fastapi import APIRouter, Response, Request, Depends, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from service.role import (get_all,
                            get_one,
                            create,
                            replace,
                            modify,
                            delete)

from model.bank import Bank
from model.user import User

from schema.bank import BankResponse

from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/api/bank', tags=['API'])


@router.get('/list')
async def get_spec_job_titles_html(request: Request, user: User = Depends(get_current_user)):
    spec_job_titles = await get_all()
    return spec_job_titles

@router.post('/create')
async def post_create_bank(bank: BankResponse):
    error_msg = None
    bank = Bank(name=bank.name,
                bik=bank.bik,
                inn=bank.inn,
                description=bank.description)
    try:
        bank = await create(bank = bank)
        create_ok = True
        return JSONResponse({"id": bank.id,
                            "name": bank.name,
                            "bik": bank.bik,
                            "inn": bank.inn,
                            "description": bank.description})

    except Duplicate:
        error_msg = "Банк с таким именем уже существует!"
        banks = get_all()
        return False

    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        banks = get_all()
        return False