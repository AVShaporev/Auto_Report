from sqlalchemy import select, update

from model.equipment import Equipment
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Equipment:
    name, country, description = row
    return Equipment(name=name,
                    spec_equipment_id=spec_equipment_id,
                    description=description)

def model_to_dict(equipment: Equipment) -> dict:
    return equipment.dict()

# Функция добавления оборудования в БД
async def create(equipment: Equipment) -> bool:
    async with new_session() as session:
        session.add(equipment)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного наименования оборудования по id
async def get_one(id: int) -> Equipment:
    async with new_session() as session:
        query = select(Equipment).filter(Equipment.id == id)
        res = await session.execute(query)
        equipment = res.scalars().all()[0]
        return equipment

# Функция запроса списка оборудования из БД
async def get_all() -> list[Equipment] | None:
    async with new_session() as session:
        query = select(Equipment)
        res = await session.execute(query)
        equipments = res.scalars().all()
    return equipments

# Функция изменения данных оборудования
async def modify(equipment: Equipment):
    async with new_session() as session:
        query = select(Equipment).where(Equipment.id == equipment.id)
        res = await session.execute(query)
        orig_equipment = res.scalars(res).one()
        orig_equipment.id = equipment.id
        orig_equipment.description = equipment.description
        await session.commit()
        return await get_one(equipment.id)

# Функция удаления записи об оборудовании из БД
async def delete(id: int) -> bool:
    equipment = await get_one(id)
    async with new_session() as session:
        await session.delete(equipment)
        await session.commit()
        return True