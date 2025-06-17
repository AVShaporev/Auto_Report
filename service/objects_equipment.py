from model.objects_equipment import Objects_Equipment
import data.objects_equipment as data


def get_all() -> list[Objects_Equipment]:
    return data.get_all()

def get_one(id: str) -> Objects_Equipment:
    return data.get_one_by_id(id)

def get_list_by_id_object(id_object: int) -> list[Objects_Equipment]:
    return data.get_list_by_id_object(id_object)

def create(objects_equipment: Objects_Equipment) -> Objects_Equipment:
    return data.create(objects_equipment)

def replace(objects_equipment: Objects_Equipment) -> Objects_Equipment:
    return data.replace(objects_equipment)

def modify(objects_equipment: Objects_Equipment) -> Objects_Equipment:
    return data.modify(objects_equipment)

def delete(name: str) -> bool:
    return data.delete(name)