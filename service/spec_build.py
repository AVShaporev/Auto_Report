from model.spec_build import Spec_Build
import data.spec_build as data


def get_all() -> list[Spec_Build]:
    return data.get_all()

def get_one(id: str) -> Spec_Build:
    return data.get_one_by_id(id)

def create(spec_build: Spec_Build) -> Spec_Build:
    return data.create(spec_build)

def replace(spec_build: Spec_Build) -> Spec_Build:
    return data.replace(spec_build)

def modify(spec_build: Spec_Build) -> Spec_Build:
    return data.modify(spec_build)

def delete(name: str) -> bool:
    return data.delete(name)