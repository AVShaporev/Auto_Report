from model.region import Region
import data.region as data


def get_all() -> list[Region]:
    return data.get_all()

def get_one(id: str) -> Region:
    return data.get_one_by_id(id)

def create(region: Region) -> Region:
    return data.create(Region)

def replace(region: Region) -> Region:
    return data.replace(region)

def modify(region: Region) -> Region:
    return data.modify(region)

def delete(name: str) -> bool:
    return data.delete(name)