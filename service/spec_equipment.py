# from model.spec_equipment import Spec_Equipment
from model.dao import Spec_Equipment_DAO as Spec_Equipment
# import data.spec_equipment as data
from data.base import BaseDAO as data                           #универсальная модель для всех 
                                                                #моделей для работы с БД

def get_all() -> list[Spec_Equipment]:
    return data.get_all(Spec_Equipment)

def get_one(id: str) -> Spec_Equipment:
    return data.get_one_by_id(id)

def create(spec_equipment: Spec_Equipment) -> Spec_Equipment:
    return data.create(spec_equipment)

def replace(spec_equipment: Spec_Equipment) -> Spec_Equipment:
    return data.replace(spec_equipment)

def modify(spec_equipment: Spec_Equipment) -> Spec_Equipment:
    return data.modify(spec_equipment)

def delete(name: str) -> bool:
    return data.delete(name)