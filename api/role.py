from datetime import datetime

from fastapi import (
                        APIRouter,
                        Response,
                        Request,
                        Depends,
                        Form,
                        Depends,
                        HTTPException,
                        status
                    )
from fastapi.responses import HTMLResponse, JSONResponse

from service.role import (get_all,
                            get_one,
                            create,
                            replace,
                            modify,
                            delete_by_name,
                            delete_by_id)

from model.user import User
from model.role import Role

from schema.role import RoleResponse

from errors import Duplicate, Missing, BaseLocking
from service.auth import (get_current_user)

router = APIRouter(prefix='/api/role', tags=['API'])


@router.get('/list')
async def get_all_roles(request: Request, user: User = Depends(get_current_user)):
    if user:
        if user.role.role_read:
            roles = await get_all()
            return roles
    return None

@router.post('/create')
# async def post_create_role(role: RoleResponse, user: User = Depends(get_current_user)):
async def post_create_role(request: Request,
                            role: RoleResponse,
                            user: User = Depends(get_current_user)):
    error_msg = None
    role = Role(name=role.name,
                description=role.description,

                # признак админитративной роли
                is_admin=role.is_admin,
                is_superadmin=role.is_superadmin,


                # права на пользователей
                user_read=role.user_read,
                user_modify=role.user_modify,
                user_create=role.user_create,
                user_delete=role.user_delete,


                # права на роли
                role_read=role.role_read,
                role_modify=role.role_modify,
                role_create=role.role_create,
                role_delete=role.role_delete,


                # права на типы регионов
                spec_region_read=role.spec_region_read,
                spec_region_modify=role.spec_region_modify,
                spec_region_create=role.spec_region_create,
                spec_region_delete=role.spec_region_delete,


                # права на регионы
                region_read=role.region_read,
                region_modify=role.region_modify,
                region_create=role.region_create,
                region_delete=role.region_delete,


                # права на типы районов
                spec_arial_read=role.spec_arial_read,
                spec_arial_modify=role.spec_arial_modify,
                spec_arial_create=role.spec_arial_create,
                spec_arial_delete=role.spec_arial_delete,


                # права на районы
                arial_read=role.arial_read,
                arial_modify=role.arial_modify,
                arial_create=role.arial_create,
                arial_delete=role.arial_delete,


                # права на типы нас.пунктов
                spec_locality_read=role.spec_locality_read,
                spec_locality_modify=role.spec_locality_modify,
                spec_locality_create=role.spec_locality_create,
                spec_locality_delete=role.spec_locality_delete,


                # права на нас.пункты
                locality_read=role.locality_read,
                locality_modify=role.locality_modify,
                locality_create=role.locality_create,
                locality_delete=role.locality_delete,


                # права на типы улиц
                spec_street_read=role.spec_street_read,
                spec_street_modify=role.spec_street_modify,
                spec_street_create=role.spec_street_create,
                spec_street_delete=role.spec_street_delete,


                # права на улицы
                street_read=role.street_read,
                street_modify=role.street_modify,
                street_create=role.street_create,
                street_delete=role.street_delete,


                # права на типы строений
                spec_build_read=role.spec_build_read,
                spec_build_modify=role.spec_build_modify,
                spec_build_create=role.spec_build_create,
                spec_build_delete=role.spec_build_delete,


                # права на типы помещений
                spec_room_read=role.spec_room_read,
                spec_room_modify=role.spec_room_modify,
                spec_room_create=role.spec_room_create,
                spec_room_delete=role.spec_room_delete,


                # права на банки
                bank_read=role.bank_read,
                bank_modify=role.bank_modify,
                bank_create=role.bank_create,
                bank_delete=role.bank_delete,


                # права на организации
                organization_read=role.organization_read,
                organization_modify=role.organization_modify,
                organization_create=role.organization_create,
                organization_delete=role.organization_delete,


                # права на типы контрактов
                spec_contract_read=role.spec_contract_read,
                spec_contract_modify=role.spec_contract_modify,
                spec_contract_create=role.spec_contract_create,
                spec_contract_delete=role.spec_contract_delete,


                # права на контракты
                contract_read=role.contract_read,
                contract_modify=role.contract_modify,
                contract_create=role.contract_create,
                contract_delete=role.contract_delete,


                # права на периоды
                period_read=role.period_read,
                period_modify=role.period_modify,
                period_create=role.period_create,
                period_delete=role.period_delete,


                # права на типы оборудования
                spec_equipment_read=role.spec_equipment_read,
                spec_equipment_modify=role.spec_equipment_modify,
                spec_equipment_create=role.spec_equipment_create,
                spec_equipment_delete=role.spec_equipment_delete,


                # права на оборудование
                equipment_read=role.equipment_read,
                equipment_modify=role.equipment_modify,
                equipment_create=role.equipment_create,
                equipment_delete=role.equipment_delete,


                # права на объекты
                object_read=role.object_read,
                object_modify=role.object_modify,
                object_create=role.object_create,
                object_delete=role.object_delete,


                # права на оборудование на объектах
                object_equipment_read=role.object_equipment_read,
                object_equipment_modify=role.object_equipment_modify,
                object_equipment_create=role.object_equipment_create,
                object_equipment_delete=role.object_equipment_delete,


                # права на операции для оборудования
                operation_read=role.operation_read,
                operation_modify=role.operation_modify,
                operation_create=role.operation_create,
                operation_delete=role.operation_delete,
                )
    
    if user:
        if user.role.role_create:
            try:
                role = await create(role = role)
                create_ok = True
                return JSONResponse({"id": role.id,
                                    "name": role.name})

            except Duplicate:
                error_msg = "Роль с таким именем уже существует!"
                roles = get_all()
                return False

            except BaseLocking:
                error_msg = "База данных недоступна для записи!"
                roles = get_all()
                return False
        return None
# 
@router.delete('/{role_id}')
async def delete(request: Request, user: User = Depends(get_current_user), role_id: int = None):
    if user:
        if user.role.role_delete:
            try:
                res = await delete_by_id(role_id)
                return res
            except BaseLocking:
                error_msg = "База данных недоступна для записи!"
                roles = get_all()
                return False
        else:
            raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У Вас недостаточно прав для удаления ролей"
            )
    else:
            raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У Вас недостаточно прав для удаления ролей"
            )
    return None

@router.put('/{role_id}')
async def put_modify_role(
                            role_id: int,
                            role: RoleResponse,
                            user: User = Depends(get_current_user)
                            ):

    error_msg = None
    role = RoleResponse(name=role.name,
                        description=role.description,

                        # признак админитративной роли
                        is_admin=role.is_admin,
                        is_superadmin=role.is_superadmin,

                        # права на пользователей
                        user_read=role.user_read,
                        user_modify=role.user_modify,
                        user_create=role.user_create,
                        user_delete=role.user_delete,

                        # права на роли
                        role_read=role.role_read,
                        role_modify=role.role_modify,
                        role_create=role.role_create,
                        role_delete=role.role_delete,

                        # права на типы регионов
                        spec_region_read=role.spec_region_read,
                        spec_region_modify=role.spec_region_modify,
                        spec_region_create=role.spec_region_create,
                        spec_region_delete=role.spec_region_delete,

                        # права на регионы
                        region_read=role.region_read,
                        region_modify=role.region_modify,
                        region_create=role.region_create,
                        region_delete=role.region_delete,

                        # права на типы районов
                        spec_arial_read=role.spec_arial_read,
                        spec_arial_modify=role.spec_arial_modify,
                        spec_arial_create=role.spec_arial_create,
                        spec_arial_delete=role.spec_arial_delete,

                        # права на районы
                        arial_read=role.arial_read,
                        arial_modify=role.arial_modify,
                        arial_create=role.arial_create,
                        arial_delete=role.arial_delete,

                        # права на типы нас.пунктов
                        spec_locality_read=role.spec_locality_read,
                        spec_locality_modify=role.spec_locality_modify,
                        spec_locality_create=role.spec_locality_create,
                        spec_locality_delete=role.spec_locality_delete,

                        # права на нас.пункты
                        locality_read=role.locality_read,
                        locality_modify=role.locality_modify,
                        locality_create=role.locality_create,
                        locality_delete=role.locality_delete,

                        # права на типы улиц
                        spec_street_read=role.spec_street_read,
                        spec_street_modify=role.spec_street_modify,
                        spec_street_create=role.spec_street_create,
                        spec_street_delete=role.spec_street_delete,

                        # права на улицы
                        street_read=role.street_read,
                        street_modify=role.street_modify,
                        street_create=role.street_create,
                        street_delete=role.street_delete,

                        # права на типы строений
                        spec_build_read=role.spec_build_read,
                        spec_build_modify=role.spec_build_modify,
                        spec_build_create=role.spec_build_create,
                        spec_build_delete=role.spec_build_delete,

                        # права на типы помещений
                        spec_room_read=role.spec_room_read,
                        spec_room_modify=role.spec_room_modify,
                        spec_room_create=role.spec_room_create,
                        spec_room_delete=role.spec_room_delete,

                        # права на банки
                        bank_read=role.bank_read,
                        bank_modify=role.bank_modify,
                        bank_create=role.bank_create,
                        bank_delete=role.bank_delete,

                        # права на организации
                        organization_read=role.organization_read,
                        organization_modify=role.organization_modify,
                        organization_create=role.organization_create,
                        organization_delete=role.organization_delete,

                        # права на типы контрактов
                        spec_contract_read=role.spec_contract_read,
                        spec_contract_modify=role.spec_contract_modify,
                        spec_contract_create=role.spec_contract_create,
                        spec_contract_delete=role.spec_contract_delete,

                        # права на контракты
                        contract_read=role.contract_read,
                        contract_modify=role.contract_modify,
                        contract_create=role.contract_create,
                        contract_delete=role.contract_delete,

                        # права на периоды
                        period_read=role.period_read,
                        period_modify=role.period_modify,
                        period_create=role.period_create,
                        period_delete=role.period_delete,

                        # права на типы оборудования
                        spec_equipment_read=role.spec_equipment_read,
                        spec_equipment_modify=role.spec_equipment_modify,
                        spec_equipment_create=role.spec_equipment_create,
                        spec_equipment_delete=role.spec_equipment_delete,

                        # права на оборудование
                        equipment_read=role.equipment_read,
                        equipment_modify=role.equipment_modify,
                        equipment_create=role.equipment_create,
                        equipment_delete=role.equipment_delete,

                        # права на объекты
                        object_read=role.object_read,
                        object_modify=role.object_modify,
                        object_create=role.object_create,
                        object_delete=role.object_delete,

                        # права на оборудование на объектах
                        object_equipment_read=role.object_equipment_read,
                        object_equipment_modify=role.object_equipment_modify,
                        object_equipment_create=role.object_equipment_create,
                        object_equipment_delete=role.object_equipment_delete,

                        # права на операции для оборудования
                        operation_read=role.operation_read,
                        operation_modify=role.operation_modify,
                        operation_create=role.operation_create,
                        operation_delete=role.operation_delete,
                        )
    
    if user:
        if user.role.role_modify:
            try:
                role = await modify(role_id = role_id, role = role)
                modify_ok = True
                return JSONResponse({"id": role.id,
                                    "name": role.name})

            except Duplicate:
                error_msg = "Роль с таким именем уже существует!"
                roles = get_all()
                return False

            except BaseLocking:
                error_msg = "База данных недоступна для записи!"
                roles = get_all()
                return False
        return None