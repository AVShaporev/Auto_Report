from sqlalchemy import select, update

from model.role import Role
from database.database import async_session_maker as new_session


# Функция перевода из строки в модель
def row_to_model(row: tuple) -> Role:
    name, userrole, = row
    return CreaUserure(name=name,
                    hash=hash,
                    userrole=userrole)

# Функция из модели в строку
def model_to_dict(role: Role) -> dict:
    return report.dict()

# Функция добавления строки в БД
async def create(role: Role) -> bool:
    async with new_session() as session:
        session.add(role)
        await session.flush()
        await session.commit()
        return True

# Функция запроса из БД всех строк
async def get_all():
    async with new_session() as session:
        roles = None
        query = select(Role)
        res = await session.execute(query)
        roles = res.scalars().all()
        # roles = [user for user in users if user.name != 'superadmin']
    return roles

# Функция запроса из БД одну строку по имени объекта
async def get_one(name: str) -> Role:
    async with new_session() as session:
        query = select(Role).filter(Role.name == name)
        res = await session.execute(query)
        role = res.scalars().one_or_none()
        return role

# Функция изменения строки
async def modify(role: Role):
    async with new_session() as session:
        query = select(Role).where(Role.name == role.name)
        res = await session.execute(query)
        orig_role = res.scalars(res).one()
        orig_role.name = role.name
        await session.commit()
        return await get_one(orig_role.name)


# Функция удаления из БД строки поимени
async def delete(name: str) -> bool:
    role = await get_one(name)
    async with new_session() as session:
        await session.delete(role)
        await session.commit()
        return True