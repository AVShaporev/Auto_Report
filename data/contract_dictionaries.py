import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict

from model.spec_job_title import Spec_Job_Title
from model.bank import Bank
from model.spec_contract import Spec_Contract
from model.spec_arial import Spec_Arial
from model.spec_region import Spec_Region
from model.organization import Organization
from model.region import Region
from model.arial import Arial
from model.spec_locality import Spec_Locality
from model.locality import Locality
from model.spec_street import Spec_Street
from model.street import Street
from model.spec_build import Spec_Build
from model.spec_room import Spec_Room

from utils.timer import timer

@timer
async def get_contract_dictionaries_all_spec_job_titles(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Spec_Job_Title).order_by(Spec_Job_Title.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_banks(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Bank).order_by(Bank.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_spec_contracts(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Spec_Contract).order_by(Spec_Contract.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_spec_arials(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Spec_Arial).order_by(Spec_Arial.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_spec_regions(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Spec_Region).order_by(Spec_Region.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_customers(session: AsyncSession) -> List[Dict]:
    result = await session.execute(
        select(Organization).order_by(Organization.name)
    )
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_executors(session: AsyncSession) -> List[Dict]:
    result = await session.execute(
        select(Organization).order_by(Organization.name)
    )
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_regions(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Region).order_by(Region.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_arials(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Arial))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_spec_localities(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Spec_Locality).order_by(Spec_Locality.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_localities(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Locality).order_by(Locality.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_spec_streets(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Spec_Street).order_by(Spec_Street.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_streets(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Street).order_by(Street.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_spec_builds(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Spec_Build).order_by(Spec_Build.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]

@timer
async def get_contract_dictionaries_all_spec_rooms(session: AsyncSession) -> List[Dict]:
    result = await session.execute(select(Spec_Room).order_by(Spec_Room.name))
    return [{"id": r.id, "name": r.name} for r in result.scalars()]