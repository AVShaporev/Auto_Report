from typing import Optional, List, Tuple
from schema.role import RoleCreate, RoleUpdate
from schema.pagination import PaginationParams
from database.database import new_session
from fastapi import HTTPException

from model.report import Report
import data.report as data


async def get_all() -> list[Report]:
    async with new_session() as session:
        res = await data.get_all(session)
        return res

async def get_one(id: int) -> Report:
    async with new_session() as session:
        res = await data.get_one_by_id(session, id)
        return res

async def create(report: Report) -> Report:
    async with new_session() as session:
        res = await data.create(session, report)
        return res

async def replace(report: Report) -> Report:
    async with new_session() as session:
        res = await data.replace(session, report)
        return res

async def modify(report: Report) -> Report:
    async with new_session() as session:
        res = await data.modify(session, report)
        return res

async def delete(id: int) -> bool:
    async with new_session() as session:
        res = await data.delete(session, id)
        return res