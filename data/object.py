from sqlalchemy import select, update

from model.object import Object
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Object:
    name, country, description = row
    return Object(name=name,
                    country=country,
                    description=description)

def model_to_dict(myobject: Object) -> dict:
    return myobject.dict()

# Функция добавления организации в БД
async def create(myobject: Object) -> bool:
    async with new_session() as session:
        session.add(myobject)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного организации по имени
async def get_one(name: str) -> Object:
    async with new_session() as session:
        query = select(Object).filter(Object.name == name)
        res = await session.execute(query)
        myobject = res.scalars().all()[0]
        return myobject

# Функция запроса одного организации по id
async def get_one_by_id(id: int) -> Object:
    async with new_session() as session:
        query = select(Object).filter(Object.id == id)
        res = await session.execute(query)
        myobject = res.scalars().all()[0]
        return myobject

# Функция запроса списка организаций из БД
async def get_all() -> list[Object] | None:
    async with new_session() as session:
        query = select(Object)
        res = await session.execute(query)
        myobjects = res.scalars().all()
    return myobjects

# Функция изменения данных организации
async def modify(myobject: Object):
    async with new_session() as session:
        query = select(Object).where(Object.id == myobject.id)
        res = await session.execute(query)
        orig_myobject = res.scalars(res).one()
        orig_myobject.id = myobject.id
        # orig_organization.country = organization.country
        orig_myobject.description = myobject.description
        await session.commit()
        return await get_one(myobject.id)

# Функция удаления записи об организации из БД
async def delete(id: int) -> bool:
    myobject = await get_one(id)
    async with new_session() as session:
        await session.delete(myobject)
        await session.commit()
        return True