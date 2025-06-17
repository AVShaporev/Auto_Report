from sqlalchemy import select, update

from model.objects_equipment import Objects_Equipment
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Objects_Equipment:
    name, country, description = row
    return Objects_Equipment(name=name,
                    objects_equipment_id=objects_equipment_id,
                    description=description)

def model_to_dict(objects_equipment: Objects_Equipment) -> dict:
    return objects_equipment.dict()

# Функция добавления оборудования в БД
async def create(objects_equipment: Objects_Equipment) -> bool:
    async with new_session() as session:
        session.add(objects_equipment)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного наименования оборудования по id
async def get_one_by_id(id: int) -> Objects_Equipment:
    async with new_session() as session:
        query = select(Objects_Equipment).filter(Objects_Equipment.id == id)
        res = await session.execute(query)
        objects_equipment = res.scalars().all()[0]
        return objects_equipment

# Функция запроса списка оборудования по id объекта
async def get_list_by_id_object(id: int) -> Objects_Equipment:
    async with new_session() as session:
        query = select(Objects_Equipment).filter(Objects_Equipment.object_id == id)
        res = await session.execute(query)
        objects_equipments = res.scalars().all()
        return objects_equipments

# Функция запроса списка оборудования из БД
async def get_all() -> list[Objects_Equipment] | None:
    async with new_session() as session:
        query = select(Objects_Equipment)
        res = await session.execute(query)
        objects_equipments = res.scalars().all()
    return objects_equipments

# Функция изменения данных оборудования
async def modify(objects_equipment: Objects_Equipment):
    async with new_session() as session:
        query = select(Objects_Equipment).where(Objects_Equipment.id == objects_equipment.id)
        res = await session.execute(query)
        orig_objects_equipment = res.scalars(res).one()
        orig_objects_equipment.id = objects_equipment.id
        orig_objects_equipment.description = objects_equipment.description
        await session.commit()
        return await get_one(objects_equipment.id)

# Функция удаления записи об оборудовании из БД
async def delete(id: int) -> bool:
    objects_equipment = await get_one(id)
    async with new_session() as session:
        await session.delete(objects_equipment)
        await session.commit()
        return True