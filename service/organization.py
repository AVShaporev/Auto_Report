from model.organization import Organization
import data.organization as data


def get_all() -> list[Organization]:
    return data.get_all()

def get_one(name: str) -> Organization:
    return data.get_one(name)

def create(organization: Organization) -> Organization:
    return data.create(explorer)

def replace(organization: Organization) -> Organization:
    return data.replace(explorer)

def modify(organization: Organization) -> Organization:
    return data.modify(organization)

def delete(name: str) -> bool:
    return data.delete(name)