from sqlalchemy import select, update

from model.locality import Locality
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Locality:
    name, spec_locality_id, description = row
    return Locality(name=name,
                    spec_locality_id=spec_locality_id,
                    description=description)

def model_to_dict(locality: Locality) -> dict:
    return locality.dict()

# Функция добавления организации в БД
async def create(locality: Locality) -> bool:
    async with new_session() as session:
        session.add(locality)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного организации по имени
async def get_one(name: str) -> Locality:
    async with new_session() as session:
        query = select(Locality).filter(Locality.name == name)
        res = await session.execute(query)
        locality = res.scalars().all()[0]
        return locality

# Функция запроса одного организации по id
async def get_one_by_id(id: int) -> Locality:
    async with new_session() as session:
        query = select(Locality).filter(Locality.id == id)
        res = await session.execute(query)
        locality = res.scalars().all()[0]
        return locality

# Функция запроса списка организаций из БД
async def get_all() -> list[Locality] | None:
    async with new_session() as session:
        query = select(Locality)
        res = await session.execute(query)
        localitys = res.scalars().all()
    return localitys

# Функция изменения данных организации
async def modify(contract: Locality):
    async with new_session() as session:
        query = select(Locality).where(Locality.id == locality.id)
        res = await session.execute(query)
        orig_locality = res.scalars(res).one()
        orig_locality.id = organization.id
        orig_locality.description = locality.description
        await session.commit()
        return await get_one(locality.id)

# Функция удаления записи об организации из БД
async def delete(id: int) -> bool:
    locality = await get_one(id)
    async with new_session() as session:
        await session.delete(contract)
        await session.commit()
        return True