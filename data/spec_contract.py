from sqlalchemy import select, update

from model.spec_contract import Spec_Contract
from database.database import async_session_maker as new_session


# конвертация из кортежа в модель
def row_to_model(row: tuple) -> Spec_Contract:
    name, description = row
    return Spec_Contract(name=name,
                    description=description)

# конвертация из модели в словарь
def model_to_dict(spec_contract: Spec_Contract) -> dict:
    return spec_contract.dict()

# Функция добавления типа контракта в БД
async def create(spec_contract: Spec_Contract) -> bool:
    async with new_session() as session:
        session.add(spec_contract)
        await session.flush()
        await session.commit()
        return await get_one(spec_contract.name)
 
# Функция запроса одного типа контракта по имени
async def get_one(name: str) -> Spec_Contract:
    async with new_session() as session:
        query = select(Spec_Contract).filter(Spec_Contract.name == name)
        res = await session.execute(query)
        spec_contract = res.scalars().all()[0]
        return spec_contract

# Функция запроса одного типа контракта по id
async def get_one_by_id(id: int) -> Spec_Contract:
    async with new_session() as session:
        query = select(Spec_Contract).filter(Spec_Contract.id == id)
        res = await session.execute(query)
        spec_contract = res.scalars().all()[0]
        return spec_contract

# Функция запроса списка типов контракта из БД
async def get_all() -> list[Spec_Contract] | None:
    async with new_session() as session:
        query = select(Spec_Contract)
        res = await session.execute(query)
        spec_contracts = res.scalars().all()
    return spec_contracts

# Функция изменения данных типа контракта
async def modify(spec_contract: Spec_Contract):
    async with new_session() as session:
        query = select(Spec_Contract).where(Spec_Contract.id == spec_contract.id)
        res = await session.execute(query)
        orig_spec_contract = res.scalars(res).one()
        orig_spec_contract.id = spec_contract.id
        orig_lspec_contract.description = spec_contract.description
        await session.commit()
        return await get_one(spec_contract.id)

# Функция удаления записи об типе контракта из БД
async def delete(id: int) -> bool:
    spec_contract = await get_one(id)
    async with new_session() as session:
        await session.delete(spec_contract)
        await session.commit()
        return True