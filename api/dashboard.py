from fastapi import APIRouter, Depends
from model.user import User
from schema.dashboard import DashboardStatsResponse
from service import dashboard as dashboard_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить статистику для главной страницы.
    Доступно только активным пользователям.
    """
    return await dashboard_service.get_dashboard_stats(current_user)