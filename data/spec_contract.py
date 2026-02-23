from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple

from model.spec_contract import Spec_Contract
from database.database import async_session_maker as new_session


# Функция добавления типа контракта в БД
async def create(
                    session: AsyncSession,
                    spec_contract: Spec_Contract
                    ) -> bool:
    res = await session.add(spec_contract)
    await session.commit()
    await session.refresh(role)
    return role

 
# Функция запроса одного типа контракта по номеру
async def get_by_number(
                    session: AsyncSession,
                    number: str
                    ) -> Spec_Contract:
    query = select(Spec_Contract).where(Spec_Contract.number == number)
    res = await session.execute(query)
    return res.scalar_one_or_none()

# Функция запроса одного типа контракта по id
async def get_one_by_id(
                        session: AsyncSession,
                        id: int
                        ) -> Spec_Contract:
    query = select(Spec_Contract).where(Spec_Contract.id == id)
    res = await session.execute(query)
    return res.scalar_one_or_none()

# Функция запроса списка типов контракта из БД
async def get_all(
                    session: AsyncSession
                    ) -> list[Spec_Contract] | None:
    query = select(Spec_Contract).order_by(Spec_Contract.id)
    res = await session.execute(query)
    return res.scalars().all()

# # Функция изменения данных типа контракта
# async def modify(
#                     session: AsyncSession,
#                     spec_contract: Spec_Contract
#                     ):
#     query = select(Spec_Contract).where(Spec_Contract.id == spec_contract.id)
#     res = await session.execute(query)
#     orig_spec_contract = res.scalars(res).one()
#     orig_spec_contract.id = spec_contract.id
#     orig_spec_contract.description = spec_contract.description
#     await session.commit()
#     return await get_one(spec_contract.id)

# Функция удаления записи об типе контракта из БД
async def delete(
                    session: AsyncSession,
                    id: int
                    ) -> bool:
    spec_contract = await get_one(id)
    await session.delete(spec_contract)
    await session.commit()
    return True