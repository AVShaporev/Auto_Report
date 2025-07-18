from sqlalchemy import select, update

from model.arial import Arial
from database.database import async_session_maker as new_session


# Функция перевода из строки в модель
def row_to_model(row: tuple) -> Arial:
    name, spec_arial_id, description = row
    return Arial(name=name,
                    spec_arial_id=spec_arial_id,
                    description=description)

# Функция из модели в строку
def model_to_dict(arial: Arial) -> dict:
    return arial.dict()

# Функция добавления строки в БД
async def create(arial: Arial) -> bool:
    async with new_session() as session:
        session.add(arial)
        await session.flush()
        await session.commit()
        return True

# Функция выбора всех регионов  из БД
async def get_all():
    async with new_session() as session:
        arials = None
        query = select(Arial)
        res = await session.execute(query)
        arials = res.scalars().all()
    return arials

# Функция выбора банка по имени
async def get_one(name: str) -> Arial:
    async with new_session() as session:
        query = select(Arial).filter(Arial.name == name)
        res = await session.execute(query)
        arial = res.scalars().one_or_none()
        return arial

# Функция модификации банка
async def modify(arial: Arial):
    async with new_session() as session:
        query = select(Arial).where(Arial.name == arial.name)
        res = await session.execute(query)
        orig_arial = res.scalars(res).one()
        orig_arial.name = arial.name
        await session.commit()
        return await get_one(orig_arial.name)

# Функция удаления записи о банке по имени
async def delete(name: str) -> bool:
    arial = await get_one(name)
    async with new_session() as session:
        await session.delete(arial)
        await session.commit()
        return True