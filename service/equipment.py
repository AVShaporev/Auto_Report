from model.equipment import Equipment
import data.equipment as data


def get_all() -> list[Equipment]:
    return data.get_all()

def get_one(id: int) -> Equipment:
    return data.get_one(id)

def create(equipment: Equipment) -> Equipment:
    return data.create(equipment)

def replace(equipment: Equipment) -> Equipment:
    return data.replace(equipment)

def modify(equipment: Equipment) -> Equipment:
    return data.modify(equipment)

def delete(name: str) -> bool:
    return data.delete(name)