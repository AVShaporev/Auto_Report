from typing import Optional, List, Tuple
from schema.pagination import PaginationParams
from database.database import new_session
from fastapi import HTTPException

from model.spec_contract import Spec_Contract
import data.spec_contract as data


async def get_all() -> list[Spec_Contract]:
    async with new_session() as session:
        res = await data.get_all(session)
        return res

async def get_one(id: str) -> Spec_Contract:
    async with new_session() as session:
        res = await data.get_one_by_id(session, id)
        return res

async def create(spec_contract: Spec_Contract) -> Spec_Contract:
    async with new_session() as session:
        res = await data.create(session, spec_contract)
        return res

async def replace(spec_contract: Spec_Contract) -> Spec_Contract:
    async with new_session() as session:
        res = await data.replace(session, spec_contract)
        return res

async def modify(spec_contract: Spec_Contract) -> Spec_Contract:
    async with new_session() as session:
        res = await data.modify(session, spec_contract)
        return res

async def delete(name: str) -> bool:
    async with new_session() as session:
        res = await data.delete(session, name)
        return res