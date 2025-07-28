from sqlalchemy import select, update

from model.contract import Contract
# from schema.contract import Read_Contract
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Contract:
    name, country, description = row
    return Contract(name=name,
                    country=country,
                    description=description)

def model_to_dict(contract: Contract) -> dict:
    return contract.dict()

# Функция добавления организации в БД
async def create(contract: Contract) -> bool:
    async with new_session() as session:
        session.add(contract)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного организации по имени
async def get_one(name: str) -> Contract:
    async with new_session() as session:
        query = select(Contract).filter(Contract.name == name)
        res = await session.execute(query)
        contract = res.scalars().all()[0]
        return contract

# Функция запроса одного организации по id
async def get_one_by_id(id: int) -> Contract:
    async with new_session() as session:
        query = select(Contract).filter(Contract.id == id)
        res = await session.execute(query)
        contract = res.scalars().all()[0]
        return contract

async def get_by_customer(id: int) -> list[Contract]:
    async with new_session() as session:
        query = select(Contract).filter(Contract.customer_id == id)
        res = await session.execute(query)
        contracts = res.scalars().all()
    return contracts

async def get_by_executor(id: int) -> list[Contract]:
    async with new_session() as session:
        query = select(Contract).filter(Contract.executor_id == id)
        res = await session.execute(query)
        contracts = res.scalars().all()
    return contracts

# Функция запроса списка организаций из БД
async def get_all() -> list[Contract] | None:
    async with new_session() as session:
        query = select(Contract)
        res = await session.execute(query)
        contracts = res.scalars().all()
    return contracts

# Функция изменения данных организации
async def modify(contract: Contract):
    async with new_session() as session:
        query = select(Contract).where(Contract.id == contract.id)
        res = await session.execute(query)
        orig_contract = res.scalars(res).one()
        orig_contract.id = organization.id
        # orig_organization.country = organization.country
        orig_contract.description = contract.description
        await session.commit()
        return await get_one(contract.id)

# Функция удаления записи об организации из БД
async def delete(id: int) -> bool:
    contract = await get_one(id)
    async with new_session() as session:
        await session.delete(contract)
        await session.commit()
        return True