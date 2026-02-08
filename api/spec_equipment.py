from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form, Depends

from service.spec_equipment import (get_one,
                                        get_all,
                                        create,
                                        delete,
                                        modify)

from model.spec_equipment import Spec_Equipment
from model.user import User

from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/api/spec_equipment', tags=['API'])

@router.get('/list')
async def get_all_spec_equipments(request: Request, user: User = Depends(get_current_user)):
    spec_equipments = await get_all()
    return spec_equipments

@router.post('/create')
async def post_create_spec_equipment(name,
                                        description,
                                        user: User = Depends(get_current_user)):
    error_msg = None
    spec_equipment = Spec_Equipment(name=name,
                                    description=description)
    try:
        spec_equipment = await create(spec_equipment = spec_equipment)
        spec_equipments = await get_all()
        create_ok = True
        return spec_equipment

    except Duplicate:
        error_msg = "Тип оборудования с таким именем уже существует!"
        spec_equipments = get_all()
        return False

    except BaseLocking:
        error_msg = "База данных недоступна для записи!"
        spec_equipments = get_all()
        return False

@router.get('/{spec_equipment_id}')
async def get_one(request: Request,
                    user: User = Depends(get_current_user),
                    spec_equipment_id: str = ''):
    spec_equipment = await get_one(int(spec_equipment_id))
    return spec_equipment