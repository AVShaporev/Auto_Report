from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class QuickStatsResponse(BaseModel):
    """Быстрая статистика по статусам"""
    
    pending_orders: int = Field(..., description="Ожидающие заявки")
    unresolved_issues: int = Field(..., description="Незакрытые неисправности")
    critical_issues: int = Field(..., description="Критические неисправности")

class ActivityResponse(BaseModel):
    """Элемент ленты активностей"""
    id: int
    type: str  # object, contract, order, issue, report и т.д.
    text: str
    created_at: datetime
    link: Optional[str] = Field(None, description="Ссылка на детальную страницу")

class DashboardStatsResponse(BaseModel):
    """Полный ответ со статистикой для дашборда"""
    objects: int
    contracts: int
    equipments: int
    orders: int
    issues: int
    reports: int
    quick_stats: QuickStatsResponse
    recent_activities: List[ActivityResponse]

class DashboardSpecStatsResponse(BaseModel):
    """Полный ответ для справочников"""
    spec_regions: int
    spec_arials: int
    spec_localitys: int
    spec_streets: int
    spec_builds: int
    spec_rooms: int

    spec_contracts: int
    spec_job_titles: int

    spec_equipments: int
    spec_orders:int
