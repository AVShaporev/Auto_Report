from model.spec_job_title import Spec_Job_Title
import data.spec_job_title as data


def get_all() -> list[Spec_Job_Title]:
    return data.get_all()

def get_one(id: str) -> Spec_Job_Title:
    return data.get_one_by_id(id)

def create(spec_job_title: Spec_Job_Title) -> Spec_Job_Title:
    return data.create(Spec_Job_Title)

def replace(spec_job_title: Spec_Job_Title) -> Spec_Job_Title:
    return data.replace(spec_job_title)

def modify(spec_job_title: Spec_Job_Title) -> Spec_Job_Title:
    return data.modify(spec_job_title)

def delete(name: str) -> bool:
    return data.delete(name)