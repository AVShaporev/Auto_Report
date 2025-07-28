from model.street import Street
import data.street as data


def get_all() -> list[Street]:
    return data.get_all()

def get_one(id: str) -> Street:
    return data.get_one_by_id(id)

def create(street: Street) -> Street:
    return data.create(street)

def replace(street: Street) -> Street:
    return data.replace(street)

def modify(street: Street) -> Street:
    return data.modify(street)

def delete(name: str) -> bool:
    return data.delete(name)