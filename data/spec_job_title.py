from sqlalchemy import select, update

from model.spec_job_title import Spec_Job_Title
from database.database import async_session_maker as new_session


# Функция перевода из строки в модель
def row_to_model(row: tuple) -> Spec_Job_Title:
    name, description = row
    return Spec_Job_Title(name=name,
                            description=description)

# Функция из модели в строку
def model_to_dict(spec_job_title: Spec_Job_Title) -> dict:
    return spec_job_title.dict()

# Функция добавления строки в БД
async def create(spec_job_title: Spec_Job_Title) -> bool:
    async with new_session() as session:
        session.add(spec_job_title)
        await session.flush()
        await session.commit()
        return True

# Функция выбора всех регионов  из БД
async def get_all():
    async with new_session() as session:
        spec_job_titles = None
        query = select(Spec_Job_Title)
        res = await session.execute(query)
        spec_job_titles = res.scalars().all()
    return spec_job_titles

# Функция выбора банка по имени
async def get_one(name: str) -> Spec_Job_Title:
    async with new_session() as session:
        query = select(Spec_Job_Title).filter(Spec_Job_Title.name == name)
        res = await session.execute(query)
        spec_job_title = res.scalars().one_or_none()
        return spec_job_title

# Функция модификации банка
async def modify(spec_job_title: Spec_Job_Title):
    async with new_session() as session:
        query = select(Spec_Job_Title).where(Spec_Job_Title.name == spec_job_title.name)
        res = await session.execute(query)
        orig_spec_job_title = res.scalars(res).one()
        orig_spec_job_title.name = spec_job_title.name
        await session.commit()
        return await get_one(orig_spec_job_title.name)

# Функция удаления записи о банке по имени
async def delete(name: str) -> bool:
    spec_job_title = await get_one(name)
    async with new_session() as session:
        await session.delete(spec_job_title)
        await session.commit()
        return True