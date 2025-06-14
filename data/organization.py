from sqlalchemy import select, update

from model.organization import Organization
from schema.organization import Read_Organization
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Organization:
    name, country, description = row
    return Organization(name=name,
                    country=country,
                    description=description)

def model_to_dict(organization: Organization) -> dict:
    return organization.dict()

# Функция добавления организации в БД
async def create(organization: Organization) -> bool:
    async with new_session() as session:
        session.add(organization)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного организации по имени
async def get_one(name: str) -> Organization:
    async with new_session() as session:
        query = select(Organization).filter(Organization.name == name)
        res = await session.execute(query)
        organization = res.scalars().all()[0]
        return organization

# Функция запроса одного организации по id
async def get_one_by_id(id: int) -> Organization:
    async with new_session() as session:
        query = select(Organization).filter(Organization.id == id)
        res = await session.execute(query)
        organization = res.scalars().all()[0]
        return organization

# Функция запроса списка организаций из БД
async def get_all() -> list[Organization] | None:
    async with new_session() as session:
        query = select(Organization)
        res = await session.execute(query)
        organizations = res.scalars().all()
    return organizations

# Функция изменения данных организации
async def modify(organization: Organization):
    async with new_session() as session:
        query = select(Organization).where(Organization.name == organization.name)
        res = await session.execute(query)
        orig_organization = res.scalars(res).one()
        orig_organization.name = organization.name
        # orig_organization.country = organization.country
        orig_organization.description = organization.description
        await session.commit()
        return await get_one(orig_organizationr.name)

# Функция удаления записи об организации из БД
async def delete(name: str) -> bool:
    organization = await get_one(name)
    async with new_session() as session:
        await session.delete(organization)
        await session.commit()
        return True