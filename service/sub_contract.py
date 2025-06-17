from model.sub_contract import Sub_Contract
import data.sub_contract as data


def get_all() -> list[Sub_Contract]:
    return data.get_all()

def get_one(id: str) -> Sub_Contract:
    return data.get_one_by_id(id)

def create(sub_contract: Sub_Contract) -> Sub_Contract:
    return data.create(sub_contract)

def replace(sub_contract: Sub_Contract) -> Sub_Contract:
    return data.replace(sub_contract)

def modify(sub_contract: Sub_Contract) -> Sub_Contract:
    return data.modify(sub_contract)

def delete(name: str) -> bool:
    return data.delete(name)