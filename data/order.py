from sqlalchemy import select, update

from model.order import Order

from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Order:
    number, spec_order_id, contract_id, object_id, user_id, description = row
    return Order(number=number,
                    spec_order_id=check_pass,
                    contract_id=contract_id,
                    object_id=object_id,
                    user_id=user_id,
                    description=description)

def model_to_dict(order: Order) -> dict:
    return order.dict()

# Функция добавления заявки в БД
async def create(order: Order) -> bool:
    async with new_session() as session:
        session.add(order)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одной заявки по имени
async def get_one(name: str) -> Order:
    async with new_session() as session:
        query = select(Order).filter(Order.name == name)
        res = await session.execute(query)
        order = res.scalars().all()[0]
        return order

# Функция запроса одной заявки по id
async def get_one_by_id(id: int) -> Order:
    async with new_session() as session:
        query = select(Order).filter(Order.id == id)
        res = await session.execute(query)
        order = res.scalars().all()[0]
        return order

# Функция запроса списка заявок из БД
async def get_all() -> list[Order] | None:
    async with new_session() as session:
        query = select(Order)
        res = await session.execute(query)
        orders = res.scalars().all()
    return orders

# Функция изменения данных заявки
async def modify(order: Order):
    async with new_session() as session:
        query = select(Order).where(Order.id == order.id)
        res = await session.execute(query)
        orig_order = res.scalars(res).one()
        orig_order.id = order.id
        orig_order.description = order.description
        await session.commit()
        return await get_one(order.id)

# Функция удаления записи о заявке из БД
async def delete(id: int) -> bool:
    order = await get_one(id)
    async with new_session() as session:
        await session.delete(order)
        await session.commit()
        return True