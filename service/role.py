from model.role import Role
import data.role as data


async def get_all() -> list[Role]:
    res = await data.get_all()
    return res

def get_one(name: str) -> Role:
    return data.get_one(name)

def create(name: str) -> bool:
    role = Role(name=name)
    return data.create(role)

def replace(role: Role) -> Role:
    return data.replace(role)

def modify(role: Role) -> Role:
    return data.modify(role)

def delete(name: str) -> bool:
    return data.delete(name)