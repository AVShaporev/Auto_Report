from model.role import Role
from schema.role import RoleResponse
import data.role as data


async def get_all() -> list[Role]:
    res = await data.get_all()
    return res

def get_one(name: str) -> Role:
    return data.get_one(name)

async def create(role: dict) -> Role:
    role = await data.create(role)
    return role

async def modify(role_id: int, role: RoleResponse) -> Role:
    role = await data.modify(role_id=role_id, role_update=role)
    return role

def replace(role: Role) -> Role:
    return data.replace(role)

def delete_by_name(name: str) -> bool:
    return data.delete_by_name(name)

def delete_by_id(id: int) -> bool:
    return data.delete_by_id(id)