from sqlalchemy import select, update

from model.spec_locality import Spec_Locality
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Spec_Locality:
    name, short_name, description = row
    return Spec_Locality(name=name,
                    short_name=short_name,
                    description=description)

def model_to_dict(spec_locality: Spec_Locality) -> dict:
    return spec_locality.dict()

# Функция добавления организации в БД
async def create(spec_locality: Spec_Locality) -> bool:
    async with new_session() as session:
        session.add(spec_locality)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного организации по имени
async def get_one(name: str) -> Spec_Locality:
    async with new_session() as session:
        query = select(Spec_Locality).filter(Spec_Locality.name == name)
        res = await session.execute(query)
        spec_locality = res.scalars().all()[0]
        return spec_locality

# Функция запроса одного организации по id
async def get_one_by_id(id: int) -> Spec_Locality:
    async with new_session() as session:
        query = select(Spec_Locality).filter(Spec_Locality.id == id)
        res = await session.execute(query)
        spec_locality = res.scalars().all()[0]
        return spec_locality

# Функция запроса списка организаций из БД
async def get_all() -> list[Spec_Locality] | None:
    async with new_session() as session:
        query = select(Spec_Locality)
        res = await session.execute(query)
        spec_localitys = res.scalars().all()
    return spec_localitys

# Функция изменения данных организации
async def modify(spec_locality: Spec_Locality):
    async with new_session() as session:
        query = select(Spec_Locality).where(Spec_Locality.id == spec_locality.id)
        res = await session.execute(query)
        orig_spec_locality = res.scalars(res).one()
        orig_spec_locality.id = spec_locality.id
        orig_lspec_locality.description = spec_locality.description
        await session.commit()
        return await get_one(spec_locality.id)

# Функция удаления записи об организации из БД
async def delete(id: int) -> bool:
    spec_locality = await get_one(id)
    async with new_session() as session:
        await session.delete(spec_locality)
        await session.commit()
        return True