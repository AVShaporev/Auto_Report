from sqlalchemy import select, update

from model.user import User
# from schema.user import Read_User
from database.database import async_session_maker as new_session


# # Функция перевода из строки в модель
# def row_to_model(row: tuple) -> User:
#     name, hash, userrole = row
#     return CreaUserure(name=name,
#                     hash=hash,
#                     userrole=userrole)

# Функция из модели в строку
def model_to_dict(user: User) -> dict:
    res = {}
    for k, v in user.__dict__.items():
        if k == "name":
            res[k] = v
        if k == "hash":
            res[k] = v
        if k == "role_id":
            res[k] = v                       
    return res

# Функция добавления строки в БД
async def create(user: User) -> bool:
    async with new_session() as session:
        session.add(user)
        await session.flush()
        await session.commit()
        return True

async def get_all():
    # print('user - async def get_all():')
    async with new_session() as session:
        users = None
        query = select(User)
        res = await session.execute(query)
        users = res.scalars().all()
        users = [user for user in users if user.name != 'superadmin']
    return users

async def get_one(name: str) -> User:
    async with new_session() as session:
        query = select(User).filter(
                                User.name == name
                                )
        res = await session.execute(query)
        user = res.scalars().one_or_none()
        return user

async def modify(user: User):
    async with new_session() as session:
        query = select(User).where(User.name == user.name)
        res = await session.execute(query)
        orig_user = res.scalars(res).one()
        orig_user.name = creature.name
        orig_user.hash = creature.country
        orig_user.userrole = creature.area
        await session.commit()
        return await get_one(orig_user.name)


async def delete(name: str) -> bool:
    user = await get_one(name)
    async with new_session() as session:
        await session.delete(user)
        await session.commit()
        return True