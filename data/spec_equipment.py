from sqlalchemy import select, update

from model.spec_equipment import Spec_Equipment
from database.database import async_session_maker as new_session


# Функция добавления типа оборудования
async def create(spec_equipment: Spec_Equipment) -> bool:
    async with new_session() as session:
        session.add(spec_equipment)
        await session.flush()
        await session.commit()
        return await get_one(spec_equipment.name)
 
# Функция запроса одного типа оборудования по имени
async def get_one(name: str) -> Spec_Equipment:
    async with new_session() as session:
        query = select(Spec_Equipment).filter(Spec_Equipment.name == name)
        res = await session.execute(query)
        spec_equipment = res.scalars().all()[0]
        return spec_equipment

# Функция запроса одного типа оборудования по id
async def get_one_by_id(id: int) -> Spec_Equipment:
    async with new_session() as session:
        query = select(Spec_Equipment).filter(Spec_Equipment.id == id)
        res = await session.execute(query)
        spec_equipment = res.scalars().all()[0]
        return spec_equipment

# Функция запроса списка всех типов оборудования из БД
async def get_all() -> list | None:
    async with new_session() as session:
        query = select(Spec_Equipment)
        res = await session.execute(query)
        spec_equipments = res.scalars().all()
    return spec_equipments

# Функция изменения данных типа оборудования
async def modify(spec_equipment: Spec_Equipment):
    async with new_session() as session:
        query = select(Spec_Equipment).where(Spec_Equipment.id == spec_equipment.id)
        res = await session.execute(query)
        orig_spec_equipment = res.scalars(res).one()
        orig_spec_equipment.id = spec_equipment.id
        orig_spec_equipment.description = spec_equipment.description
        await session.commit()
        return await get_one(spec_equipment.id)

# Функция удаления записи об типе оборудования из БД
async def delete(id: int) -> bool:
    spec_equipment = await get_one(id)
    async with new_session() as session:
        await session.delete(spec_equipment)
        await session.commit()
        return True