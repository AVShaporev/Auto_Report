from model.organization import Organization
import data.organization as data


def get_all() -> list[Organization]:
    return data.get_all()

def get_one(id: str) -> Organization:
    return data.get_one_by_id(id)

def create(organization: Organization) -> Organization:
    return data.create(organization)

def replace(organization: Organization) -> Organization:
    return data.replace(organization)

def modify(organization: Organization) -> Organization:
    return data.modify(organization)

def delete(name: str) -> bool:
    return data.delete(name)