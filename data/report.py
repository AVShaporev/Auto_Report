from sqlalchemy import select, update

from model.report import Report

from database.database import async_session_maker as new_session


def row_to_model(row: tuple) -> Report:
    number, check_pass, contract_id, object_id, user_id = row
    return Report(number=number,
                    check_pass=check_pass,
                    contract_id=contract_id,
                    object_id=object_id,
                    user_id=user_id)

def model_to_dict(report: Report) -> dict:
    return report.dict()

# Функция добавления организации в БД
async def create(report: Report) -> bool:
    async with new_session() as session:
        session.add(report)
        await session.flush()
        await session.commit()
        return True
 
# Функция запроса одного организации по имени
async def get_one(name: str) -> Report:
    async with new_session() as session:
        query = select(Report).filter(Report.name == name)
        res = await session.execute(query)
        report = res.scalars().all()[0]
        return report

# Функция запроса одного организации по id
async def get_one_by_id(id: int) -> Report:
    async with new_session() as session:
        query = select(Report).filter(Report.id == id)
        res = await session.execute(query)
        report = res.scalars().all()[0]
        return report

# Функция запроса списка организаций из БД
async def get_all() -> list[Report] | None:
    async with new_session() as session:
        query = select(Report)
        res = await session.execute(query)
        reports = res.scalars().all()
    return reports

# Функция изменения данных организации
async def modify(report: Report):
    async with new_session() as session:
        query = select(Report).where(Report.id == report.id)
        res = await session.execute(query)
        orig_report = res.scalars(res).one()
        orig_report.id = report.id
        orig_report.description = report.description
        await session.commit()
        return await get_one(report.id)

# Функция удаления записи об организации из БД
async def delete(id: int) -> bool:
    report = await get_one(id)
    async with new_session() as session:
        await session.delete(report)
        await session.commit()
        return True