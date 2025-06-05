from sqlalchemy import select, update

from model.spec_equipment import Spec_Equipment
from database.database import async_session_maker as new_session


# Функция запроса списка всех типов оборудования из БД
async def get_all() -> list | None:
    async with new_session() as session:
        query = select(Spec_Equipment)
        res = await session.execute(query)
        creatures = res.scalars().all()
    return spec_equipments