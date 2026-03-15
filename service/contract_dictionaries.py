import datetime

import asyncio
from fastapi import HTTPException
from model.user import User
from data import contract_dictionaries as data
from schema.contract_dictionaries import ContractDictionariesResponse, IdNameResponse
from database.database import new_session

from utils.timer import timer

@timer
async def get_contract_dictionaries(current_user: User) -> ContractDictionariesResponse:
    # При необходимости проверяем право доступа к договорам
    if not current_user.role.contract_read:
        raise HTTPException(403, "Недостаточно прав для просмотра договоров")

    async with new_session() as session:
        tasks = [
            data.get_contract_dictionaries_all_spec_job_titles(session),
            data.get_contract_dictionaries_all_banks(session),
            data.get_contract_dictionaries_all_spec_contracts(session),
            data.get_contract_dictionaries_all_spec_arials(session),
            data.get_contract_dictionaries_all_spec_regions(session),
            data.get_contract_dictionaries_customers(session),
            data.get_contract_dictionaries_executors(session),
            data.get_contract_dictionaries_all_regions(session),
            data.get_contract_dictionaries_all_arials(session),
            data.get_contract_dictionaries_all_spec_localities(session),
            data.get_contract_dictionaries_all_localities(session),
            data.get_contract_dictionaries_all_spec_streets(session),
            data.get_contract_dictionaries_all_streets(session),
            data.get_contract_dictionaries_all_spec_builds(session),
            data.get_contract_dictionaries_all_spec_rooms(session),
        ]
        results = await asyncio.gather(*tasks)

    result = ContractDictionariesResponse(
        spec_job_titles=[IdNameResponse(**item) for item in results[0]],
        banks=[IdNameResponse(**item) for item in results[1]],
        spec_contracts=[IdNameResponse(**item) for item in results[2]],
        spec_arials=[IdNameResponse(**item) for item in results[3]],
        spec_regions=[IdNameResponse(**item) for item in results[4]],
        customers=[IdNameResponse(**item) for item in results[5]],
        executors=[IdNameResponse(**item) for item in results[6]],
        regions=[IdNameResponse(**item) for item in results[7]],
        arials=[IdNameResponse(**item) for item in results[8]],
        spec_localities=[IdNameResponse(**item) for item in results[9]],
        localities=[IdNameResponse(**item) for item in results[10]],
        spec_streets=[IdNameResponse(**item) for item in results[11]],
        streets=[IdNameResponse(**item) for item in results[12]],
        spec_builds=[IdNameResponse(**item) for item in results[13]],
        spec_rooms=[IdNameResponse(**item) for item in results[14]],
    )

    return result