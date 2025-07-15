from model.order import Order
import data.order as data


def get_all() -> list[Order]:
    return data.get_all()

def get_one(id: str) -> Order:
    return data.get_one_by_id(id)

def create(order: Order) -> Order:
    return data.create(order)

def replace(order: Order) -> Order:
    return data.replace(order)

def modify(order: Order) -> Order:
    return data.modify(order)

def delete(name: str) -> bool:
    return data.delete(name)