from model.locality import Locality
import data.locality as data


def get_all() -> list[Locality]:
    return data.get_all()

def get_one(id: str) -> Locality:
    return data.get_one_by_id(id)

def create(locality: Locality) -> Locality:
    return data.create(locality)

def replace(locality: Locality) -> Locality:
    return data.replace(locality)

def modify(locality: Locality) -> Locality:
    return data.modify(locality)

def delete(name: str) -> bool:
    return data.delete(name)