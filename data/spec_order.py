from sqlalchemy import select, update

from model.spec_order import Spec_Order
from database.database import async_session_maker as new_session


# перевод из кортежа в экземпляр класса
def row_to_model(row: tuple) -> Spec_Order:
    name, short_name, description = row
    return Spec_Order(name=name,
                    short_name=short_name,
                    description=description)

# перевод из экземпляра класса в модель
def model_to_dict(spec_order: Spec_Order) -> dict:
    return spec_order.dict()

# Функция добавления типа заявки в БД
async def create(spec_order: Spec_Order) -> bool:
    async with new_session() as session:
        session.add(spec_order)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного типа заявки по имени
async def get_one(name: str) -> Spec_Order:
    async with new_session() as session:
        query = select(Spec_Order).filter(Spec_Order.name == name)
        res = await session.execute(query)
        spec_order = res.scalars().all()[0]
        return spec_order

# Функция запроса одного типа заявки по id
async def get_one_by_id(id: int) -> Spec_Order:
    async with new_session() as session:
        query = select(Spec_Order).filter(Spec_Order.id == id)
        res = await session.execute(query)
        spec_order = res.scalars().all()[0]
        return spec_order

# Функция запроса списка типов заявок из БД
async def get_all() -> list[Spec_Order] | None:
    async with new_session() as session:
        query = select(Spec_Order)
        res = await session.execute(query)
        spec_orders = res.scalars().all()
    return spec_orders

# Функция изменения данных типа заявки
async def modify(spec_order: Spec_Order):
    async with new_session() as session:
        query = select(Spec_Order).where(Spec_Order.id == spec_order.id)
        res = await session.execute(query)
        orig_spec_order = res.scalars(res).one()
        orig_spec_order.id = spec_order.id
        orig_spec_order.description = spec_order.description
        await session.commit()
        return await get_one(spec_order.id)

# Функция удаления записи об типе заявки из БД
async def delete(id: int) -> bool:
    spec_order = await get_one(id)
    async with new_session() as session:
        await session.delete(spec_order)
        await session.commit()
        return True