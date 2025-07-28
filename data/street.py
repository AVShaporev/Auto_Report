from sqlalchemy import select, update

from model.street import Street
from database.database import async_session_maker as new_session


# Функция перевода из строки в модель
def row_to_model(row: tuple) -> Street:
    name, spec_street_id, description = row
    return Street(name=name,
                    spec_street_id=spec_street_id,
                    description=description)

# Функция из модели в строку
def model_to_dict(street: Street) -> dict:
    return street.dict()

# Функция добавления строки в БД
async def create(street: Street) -> bool:
    async with new_session() as session:
        session.add(street)
        await session.flush()
        await session.commit()
        return True

# Функция выбора всех банков из БД
async def get_all():
    async with new_session() as session:
        streets = None
        query = select(Street)
        res = await session.execute(query)
        streets = res.scalars().all()
    return streets

# Функция выбора банка по имени
async def get_one(name: str) -> Street:
    async with new_session() as session:
        query = select(Street).filter(Street.name == name)
        res = await session.execute(query)
        street = res.scalars().one_or_none()
        return street

# Функция модификации банка
async def modify(street: Street):
    async with new_session() as session:
        query = select(Street).where(Street.name == street.name)
        res = await session.execute(query)
        orig_street = res.scalars(res).one()
        orig_street.name = street.name
        await session.commit()
        return await get_one(orig_street.name)

# Функция удаления записи о банке по имени
async def delete(name: str) -> bool:
    street = await get_one(name)
    async with new_session() as session:
        await session.delete(street)
        await session.commit()
        return True