from model.bank import Bank
import data.bank as data


def get_all() -> list[Bank]:
    return data.get_all()

def get_one(id: str) -> Bank:
    return data.get_one_by_id(id)

def create(bank: Bank) -> Bank:
    return data.create(bank)

def replace(bank: Bank) -> Bank:
    return data.replace(bank)

def modify(bank: Bank) -> Bank:
    return data.modify(bank)

def delete(name: str) -> bool:
    return data.delete(name)