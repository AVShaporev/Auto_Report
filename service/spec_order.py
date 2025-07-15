from model.spec_order import Spec_Order
import data.spec_order as data


def get_all() -> list[Spec_Order]:
    return data.get_all()

def get_one(id: str) -> Spec_Order:
    return data.get_one_by_id(id)

def create(spec_order: Spec_Order) -> Spec_Order:
    return data.create(spec_order)

def replace(spec_order: Spec_Order) -> Spec_Order:
    return data.replace(spec_order)

def modify(spec_order: Spec_Order) -> Spec_Order:
    return data.modify(spec_order)

def delete(name: str) -> bool:
    return data.delete(name)