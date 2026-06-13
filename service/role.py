from typing import Optional, List, Tuple
from model.role import Role
from data import role as role_data
from schema.role import RoleCreate, RoleUpdate
from schema.pagination import PaginationParams
from database.database import new_session
from fastapi import HTTPException

async def get_role_by_id(
    role_id: int,
    load_users: bool = False
) -> Optional[Role]:
    """
    Получить роль по ID
    """
    async with new_session() as session:
        res = await role_data.get_role_by_id(session, role_id, load_users)
        return res

async def get_role_by_name(
    name: str
) -> Optional[Role]:
    """
    Получить роль по названию
    """
    async with new_session() as session:
        res = await role_data.get_role_by_name(session, name)
        return res

async def get_all_roles(
    load_users: bool = False
) -> List[Role]:
    """
    Получить все роли
    """
    async with new_session() as session:
        res = await role_data.get_role_all(session, load_users)
        return res

async def get_roles_paginated(
    pagination: PaginationParams,
    search: Optional[str] = None,
    is_admin: Optional[bool] = None,
    is_superadmin: Optional[bool] = None,
    sort_by: str = "id",
    sort_order: str = "asc"
) -> Tuple[List[Role], int]:
    """
    Получить список ролей с пагинацией
    """
    async with new_session() as session:
        roles, total = await role_data.get_role_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            is_admin=is_admin,
            is_superadmin=is_superadmin,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return roles, total

async def create_role(
    role_create: RoleCreate
) -> Role:
    """
    Создать новую роль.

    Запрещаем создание ещё одной superadmin-роли через UI — иначе любой
    админ может назначить себе все права в обход is_protected. Единственная
    легитимная superadmin-роль создаётся bootstrap_admin.py при инициализации.
    """
    if role_create.is_superadmin:
        raise HTTPException(
            status_code=400,
            detail="Невозможно создать новую superadmin-роль через UI. "
                   "Единственная superadmin-роль создаётся при инициализации системы.",
        )

    async with new_session() as session:
        # Проверяем уникальность имени
        exists = await role_data.check_role_name_exists(session, role_create.name)
        if exists:
            raise HTTPException(status_code=400, detail=f"Роль с именем '{role_create.name}' уже существует")

        return await role_data.create_role(session, role_create)

async def update_role(
    role_id: int,
    role_update: RoleUpdate
) -> Role:
    """
    Обновить роль.

    Защищённую роль (is_protected=True, например superadmin) полностью
    блокируем от модификаций — иначе можно случайно снять is_superadmin
    или удалить permission-флаг и потерять доступ.
    """
    async with new_session() as session:
        # Проверяем существование роли
        role = await role_data.get_role_by_id(session, role_id)
        if not role:
            raise HTTPException(status_code=404, detail=f"Роль с id {role_id} не найдена")

        if role.is_protected:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно изменить защищённую роль '{role.name}' — "
                       f"она необходима для работы системы.",
            )

        # Запрещаем «промоушн» обычной роли до superadmin через update.
        # Существующая superadmin-роль защищена is_protected (см. выше),
        # значит role_update.is_superadmin=True может прийти только для
        # роли, которая раньше им не была — это попытка эскалации прав.
        if role_update.is_superadmin and not role.is_superadmin:
            raise HTTPException(
                status_code=400,
                detail="Невозможно повысить роль до superadmin через UI. "
                       "Единственная superadmin-роль создаётся при инициализации системы.",
            )

        # Проверяем уникальность имени, если оно меняется
        if role_update.name and role_update.name != role.name:
            exists = await role_data.check_role_name_exists(session, role_update.name, role_id)
            if exists:
                raise HTTPException(status_code=400, detail=f"Роль с именем '{role_update.name}' уже существует")

        return await role_data.update_role(session, role_id, role_update)

async def delete_role(
    role_id: int
) -> bool:
    """
    Удалить роль. Защищённые (is_protected=True) — нельзя.
    """
    async with new_session() as session:
        role = await role_data.get_role_by_id(session, role_id)
        if not role:
            raise HTTPException(status_code=404, detail=f"Роль с id {role_id} не найдена")

        if role.is_protected:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить защищённую роль '{role.name}' — "
                       f"она необходима для работы системы.",
            )

        try:
            res = await role_data.delete_role(session, role_id)
            return res
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))