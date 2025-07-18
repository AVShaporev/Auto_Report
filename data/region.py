from sqlalchemy import select, update

from model.region import Region
from database.database import async_session_maker as new_session


# Функция перевода из строки в модель
def row_to_model(row: tuple) -> Region:
    name, symbol, spec_region_id, description = row
    return Region(name=name,
                    symbol=symbol,
                    spec_region_id=spec_region_id,
                    description=description)

# Функция из модели в строку
def model_to_dict(region: Region) -> dict:
    return region.dict()

# Функция добавления строки в БД
async def create(region: Region) -> bool:
    async with new_session() as session:
        session.add(region)
        await session.flush()
        await session.commit()
        return True

# Функция выбора всех регионов  из БД
async def get_all():
    async with new_session() as session:
        regions = None
        query = select(Region)
        res = await session.execute(query)
        regions = res.scalars().all()
    return regions

# Функция выбора банка по имени
async def get_one(name: str) -> Region:
    async with new_session() as session:
        query = select(Region).filter(Region.name == name)
        res = await session.execute(query)
        region = res.scalars().one_or_none()
        return region

# Функция модификации банка
async def modify(region: Region):
    async with new_session() as session:
        query = select(Region).where(Region.name == region.name)
        res = await session.execute(query)
        orig_region = res.scalars(res).one()
        orig_region.name = region.name
        await session.commit()
        return await get_one(orig_region.name)

# Функция удаления записи о банке по имени
async def delete(name: str) -> bool:
    region = await get_one(name)
    async with new_session() as session:
        await session.delete(region)
        await session.commit()
        return True