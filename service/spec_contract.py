from model.spec_contract import Spec_Contract
import data.spec_contract as data


def get_all() -> list[Spec_Contract]:
    return data.get_all()

def get_one(id: str) -> Spec_Contract:
    return data.get_one_by_id(id)

def create(spec_contract: Spec_Contract) -> Spec_Contract:
    return data.create(spec_contract)

def replace(spec_contract: Spec_Contract) -> Spec_Contract:
    return data.replace(spec_contract)

def modify(spec_contract: Spec_Contract) -> Spec_Contract:
    return data.modify(spec_contract)

def delete(name: str) -> bool:
    return data.delete(name)