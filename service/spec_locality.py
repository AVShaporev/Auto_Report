from model.spec_locality import Spec_Locality
import data.spec_locality as data


def get_all() -> list[Spec_Locality]:
    return data.get_all()

def get_one(id: str) -> Spec_Locality:
    return data.get_one_by_id(id)

def create(spec_locality: Spec_Locality) -> Spec_Locality:
    return data.create(spec_locality)

def replace(spec_locality: Spec_Locality) -> Spec_Locality:
    return data.replace(spec_locality)

def modify(spec_locality: Spec_Locality) -> Spec_Locality:
    return data.modify(spec_locality)

def delete(name: str) -> bool:
    return data.delete(name)