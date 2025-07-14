from model.report import Report
import data.report as data


def get_all() -> list[Report]:
    return data.get_all()

def get_one(id: str) -> Report:
    return data.get_one_by_id(id)

def create(report: Report) -> Report:
    return data.create(report)

def replace(report: Report) -> Report:
    return data.replace(report)

def modify(report: Report) -> Report:
    return data.modify(report)

def delete(name: str) -> bool:
    return data.delete(name)