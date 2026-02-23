from typing import Optional, List, Tuple
from schema.role import RoleCreate, RoleUpdate
from schema.pagination import PaginationParams
from database.database import new_session
from fastapi import HTTPException

from model.order import Order
import data.order as data


async def get_all() -> list[Order]:
    async with new_session() as session:
        res = await data.get_all(session)
        return res

async def get_one(id: str) -> Order:
    async with new_session() as session:
        res = data.get_one_by_id(session, id)
        return res
async def create(order: Order) -> Order:
    async with new_session() as session:
        res = await data.create(session, order)
        return res

async def replace(order: Order) -> Order:
    async with new_session() as session:
        res = await data.replace(session, order)
        return res

async def modify(order: Order) -> Order:
    async with new_session() as session:
        res = data.modify(session, order)
        return res

async def delete(name: str) -> bool:
    async with new_session() as session:
        res = await data.delete(session, name)
        return res