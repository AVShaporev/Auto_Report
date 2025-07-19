from model.spec_room import Spec_Room
import data.spec_room as data


def get_all() -> list[Spec_Room]:
    return data.get_all()

def get_one(id: str) -> Spec_Room:
    return data.get_one_by_id(id)

def create(spec_room: Spec_Room) -> Spec_Room:
    return data.create(spec_room)

def replace(spec_room: Spec_Room) -> Spec_Room:
    return data.replace(spec_room)

def modify(spec_room: Spec_Room) -> Spec_Room:
    return data.modify(spec_room)

def delete(name: str) -> bool:
    return data.delete(name)