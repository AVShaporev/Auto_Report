from sqlalchemy import select, update

from model.sub_contract import Sub_Contract
# from schema.contract import Read_Contract
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Sub_Contract:
    name, country, description = row
    return Sub_Contract(name=name,
                    country=country,
                    description=description)

def model_to_dict(sub_contract: Sub_Contract) -> dict:
    return sub_contract.dict()

# Функция добавления организации в БД
async def create(sub_contract: Sub_Contract) -> bool:
    async with new_session() as session:
        session.add(sub_contract)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного организации по имени
async def get_one(name: str) -> Sub_Contract:
    async with new_session() as session:
        query = select(Sub_Contract).filter(Sub_Contract.name == name)
        res = await session.execute(query)
        sub_contract = res.scalars().all()[0]
        return sub_contract

# Функция запроса одного организации по id
async def get_one_by_id(id: int) -> Sub_Contract:
    async with new_session() as session:
        query = select(Sub_Contract).filter(Sub_Contract.id == id)
        res = await session.execute(query)
        sub_contract = res.scalars().all()[0]
        return sub_contract

# Функция запроса списка организаций из БД
async def get_all() -> list[Sub_Contract] | None:
    async with new_session() as session:
        query = select(Sub_Contract)
        res = await session.execute(query)
        sub_contracts = res.scalars().all()
    return sub_contracts

# Функция изменения данных организации
async def modify(sub_contract: Sub_Contract):
    async with new_session() as session:
        query = select(Sub_Contract).where(Sub_Contract.id == sub_contract.id)
        res = await session.execute(query)
        orig_sub_contract = res.scalars(res).one()
        orig_sub_contract.id = sub_contract.id
        # orig_organization.country = organization.country
        orig_sub_contract.description = sub_contract.description
        await session.commit()
        return await get_one(sub_contract.id)

# Функция удаления записи об организации из БД
async def delete(id: int) -> bool:
    sub_contract = await get_one(id)
    async with new_session() as session:
        await session.delete(contsub_contractract)
        await session.commit()
        return True