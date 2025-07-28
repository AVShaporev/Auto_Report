from sqlalchemy import select, update

from model.spec_build import Spec_Build
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Spec_Build:
    name, description = row
    return Spec_Build(name=name,
                    description=description)

def model_to_dict(spec_build: Spec_Build) -> dict:
    return spec_build.dict()

# Функция добавления типа строения в БД
async def create(spec_build: Spec_Build) -> bool:
    async with new_session() as session:
        session.add(spec_build)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного типа строения по имени
async def get_one(name: str) -> Spec_Build:
    async with new_session() as session:
        query = select(Spec_Build).filter(Spec_Build.name == name)
        res = await session.execute(query)
        spec_build = res.scalars().all()[0]
        return spec_build

# Функция запроса одного типа строения по id
async def get_one_by_id(id: int) -> Spec_Build:
    async with new_session() as session:
        query = select(Spec_Build).filter(Spec_Build.id == id)
        res = await session.execute(query)
        spec_build = res.scalars().all()[0]
        return spec_build

# Функция запроса списка типов строений из БД
async def get_all() -> list[Spec_Build] | None:
    async with new_session() as session:
        query = select(Spec_Build)
        res = await session.execute(query)
        spec_builds = res.scalars().all()
    return spec_builds

# Функция изменения данных типа строения
async def modify(spec_build: Spec_Build):
    async with new_session() as session:
        query = select(Spec_Build).where(Spec_Build.id == spec_build.id)
        res = await session.execute(query)
        orig_spec_build = res.scalars(res).one()
        orig_spec_build.id = spec_build.id
        orig_lspec_build.description = spec_build.description
        await session.commit()
        return await get_one(spec_build.id)

# Функция удаления записи об типе строения из БД
async def delete(id: int) -> bool:
    spec_build = await get_one(id)
    async with new_session() as session:
        await session.delete(spec_build)
        await session.commit()
        return True