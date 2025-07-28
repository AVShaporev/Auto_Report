from sqlalchemy import select, update

from model.bank import Bank
from database.database import async_session_maker as new_session


# Функция перевода из строки в модель
def row_to_model(row: tuple) -> Bank:
    name, bik, inn, description = row
    return Bank(name=name,
                bik=bik,
                inn=inn,
                description=description)

# Функция из модели в строку
def model_to_dict(bank: Bank) -> dict:
    return bank.dict()

# Функция добавления строки в БД
async def create(bank: Bank) -> bool:
    async with new_session() as session:
        session.add(bank)
        await session.flush()
        await session.commit()
        bank = await get_one(bank.name)
        return bank

# Функция выбора всех банков из БД
async def get_all():
    async with new_session() as session:
        banks = None
        query = select(Bank)
        res = await session.execute(query)
        banks = res.scalars().all()
    return banks

# Функция выбора банка по имени
async def get_one(name: str) -> Bank:
    async with new_session() as session:
        query = select(Bank).filter(Bank.name == name)
        res = await session.execute(query)
        bank = res.scalars().one_or_none()
        return bank

# Функция модификации банка
async def modify(bank: Bank):
    async with new_session() as session:
        query = select(Bank).where(Bank.name == bank.name)
        res = await session.execute(query)
        orig_bank = res.scalars(res).one()
        orig_bank.name = bank.name
        await session.commit()
        return await get_one(orig_bank.name)

# Функция удаления записи о банке по имени
async def delete(name: str) -> bool:
    bank = await get_one(name)
    async with new_session() as session:
        await session.delete(bank)
        await session.commit()
        return True