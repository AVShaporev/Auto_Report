from model.contract import Contract
import data.contract as data


def get_all() -> list[Contract]:
    return data.get_all()

def get_one(id: str) -> Contract:
    return data.get_one_by_id(id)

def get_by_customer(id_organization: int) -> list[Contract]:
    return data.get_by_customer(id_organization)

def get_by_executor(id_organization: int) -> list[Contract]:
    return data.get_by_executor(id_organization)

def create(contract: Contract) -> Contract:
    return data.create(contract)

def replace(contract: Contract) -> Contract:
    return data.replace(contract)

def modify(contract: Contract) -> Contract:
    return data.modify(contract)

def delete(name: str) -> bool:
    return data.delete(name)