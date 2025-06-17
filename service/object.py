from model.object import Object
import data.object as data


def get_all() -> list[Object]:
    return data.get_all()

def get_one(id: str) -> Object:
    return data.get_one_by_id(id)

def create(myobject: Object) -> Object:
    return data.create(myobject)

def replace(myobject: Object) -> Object:
    return data.replace(myobject)

def modify(myobject: Object) -> Object:
    return data.modify(myobject)

def delete(name: str) -> bool:
    return data.delete(name)