from model.arial import Arial
import data.arial as data


def get_all() -> list[Arial]:
    return data.get_all()

def get_one(id: str) -> Arial:
    return data.get_one_by_id(id)

def create(arial: Arial) -> Arial:
    return data.create(arial)

def replace(arial: Arial) -> Arial:
    return data.replace(arial)

def modify(arial: Arial) -> Arial:
    return data.modify(arial)

def delete(name: str) -> bool:
    return data.delete(name)