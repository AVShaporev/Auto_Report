from sqlalchemy import select, func, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

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
async def create(
                session: AsyncSession,
                order: Order
                ) -> bool:
    session.add(order)
    await session.flush()
    await session.commit()
    return True
 
# Функция запроса одной заявки по имени
async def get_one(
                    session: AsyncSession,
                    name: str
                    ) -> Order:
    query = select(Order).filter(Order.name == name)
    res = await session.execute(query)
    order = res.scalars().all()[0]
    return order

# Функция запроса одной заявки по id
async def get_one_by_id(
                        session: AsyncSession,
                        id: int
                        ) -> Order:
    query = select(Order).filter(Order.id == id)
    res = await session.execute(query)
    order = res.scalars().all()[0]
    return order

# Функция запроса списка заявок из БД
async def get_all(
                    session: AsyncSession
                    ) -> list[Order] | None:
    query = select(Order)
    res = await session.execute(query)
    orders = res.scalars().all()
    return orders

# Функция изменения данных заявки
async def modify(
                    session: AsyncSession,
                    order: Order
                    ):
    query = select(Order).where(Order.id == order.id)
    res = await session.execute(query)
    orig_order = res.scalars(res).one()
    orig_order.id = order.id
    orig_order.description = order.description
    await session.commit()
    return await get_one(order.id)

# Функция удаления записи о заявке из БД
async def delete(
                    session: AsyncSession,
                    id: int
                    ) -> bool:
    order = await get_one(id)
    await session.delete(order)
    await session.commit()
    return True