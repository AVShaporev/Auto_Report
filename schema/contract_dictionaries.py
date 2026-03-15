from pydantic import BaseModel
from typing import List

class IdNameResponse(BaseModel):
    id: int
    name: str

class ContractDictionariesResponse(BaseModel):
    spec_job_titles: List[IdNameResponse]   # типы должностей
    banks: List[IdNameResponse]              # банки
    spec_contracts: List[IdNameResponse]     # типы контрактов
    spec_arials: List[IdNameResponse]        # типы районов
    spec_regions: List[IdNameResponse]       # типы регионов
    customers: List[IdNameResponse]          # организации-заказчики
    executors: List[IdNameResponse]          # организации-подрядчики
    regions: List[IdNameResponse]            # регионы
    arials: List[IdNameResponse]             # районы
    spec_localities: List[IdNameResponse]    # типы населённых пунктов
    localities: List[IdNameResponse]         # населённые пункты
    spec_streets: List[IdNameResponse]       # типы улиц
    streets: List[IdNameResponse]            # улицы
    spec_builds: List[IdNameResponse]        # типы строений
    spec_rooms: List[IdNameResponse]         # типы помещений