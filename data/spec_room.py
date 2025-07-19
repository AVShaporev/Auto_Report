from sqlalchemy import select, update

from model.spec_room import Spec_Room
from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Spec_Room:
    name, short_name, description = row
    return Spec_Room(name=name,
                    short_name=short_name,
                    description=description)

def model_to_dict(spec_room: Spec_Room) -> dict:
    return spec_room.dict()

# Функция добавления типа помещения в БД
async def create(spec_room: Spec_Room) -> bool:
    async with new_session() as session:
        session.add(spec_room)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного типа помещения по имени
async def get_one(name: str) -> Spec_Room:
    async with new_session() as session:
        query = select(Spec_Room).filter(Spec_Room.name == name)
        res = await session.execute(query)
        spec_room = res.scalars().all()[0]
        return spec_room

# Функция запроса одного типа помещения по id
async def get_one_by_id(id: int) -> Spec_Room:
    async with new_session() as session:
        query = select(Spec_Room).filter(Spec_Room.id == id)
        res = await session.execute(query)
        spec_room = res.scalars().all()[0]
        return spec_room

# Функция запроса списка типов помещений из БД
async def get_all() -> list[Spec_Room] | None:
    async with new_session() as session:
        query = select(Spec_Room)
        res = await session.execute(query)
        spec_rooms = res.scalars().all()
    return spec_rooms

# Функция изменения данных типа помещения
async def modify(spec_room: Spec_Room):
    async with new_session() as session:
        query = select(Spec_Room).where(Spec_Room.id == spec_room.id)
        res = await session.execute(query)
        orig_spec_room = res.scalars(res).one()
        orig_spec_room.id = spec_room.id
        orig_lspec_room.description = spec_room.description
        await session.commit()
        return await get_one(spec_room.id)

# Функция удаления записи об типе помещения из БД
async def delete(id: int) -> bool:
    spec_room = await get_one(id)
    async with new_session() as session:
        await session.delete(spec_room)
        await session.commit()
        return True