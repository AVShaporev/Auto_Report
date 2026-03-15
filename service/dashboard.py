from typing import List
from fastapi import HTTPException
from model.user import User
from data import dashboard as dashboard_data
from schema.dashboard import (
    DashboardStatsResponse,
    QuickStatsResponse,
    ActivityResponse
)
from database.database import new_session

async def get_dashboard_stats(current_user: User) -> DashboardStatsResponse:
    """
    Сервис для получения статистики дашборда.
    Проверяет, что пользователь активен (уже гарантировано зависимостью),
    и при необходимости можно добавить более детальные проверки прав.
    """
    # Пример дополнительной проверки: если у пользователя нет прав на чтение ни одной сущности,
    # можно вернуть 403. Здесь для простоты оставляем как есть.
    # if not (current_user.role.objects_read or current_user.role.contracts_read ...):
    #     raise HTTPException(403, "Недостаточно прав для просмотра дашборда")

    async with new_session() as session:
        # Получаем статистику
        stats_data = await dashboard_data.get_dashboard_stats(session)

        # Получаем активности
        activities_data = await dashboard_data.get_recent_activities(session, limit=10)

    # Формируем быструю статистику
    quick_stats = QuickStatsResponse(
        pending_orders=stats_data["pending_orders"],
        unresolved_issues=stats_data["unresolved_issues"],
        critical_issues=stats_data["critical_issues"]
    )

    # Преобразуем активности в объекты ActivityResponse
    activities = []
    type_names = {
        "object": "Объект",
        "contract": "Договор",
        "order": "Заявка",
        "issue": "Неисправность"
    }
    for act in activities_data:
        type_ru = type_names.get(act["type"], act["type"])
        text = f"Создан {type_ru}: {act['title']}"
        # Ссылка на детальную страницу (пример для фронтенда)
        link = f"/{act['type']}s/{act['id']}"  # objects, contracts, orders, issues
        activities.append(ActivityResponse(
            id=act["id"],
            type=act["type"],
            text=text,
            created_at=act["created_at"],
            link=link
        ))

    return DashboardStatsResponse(
        objects=stats_data["objects"],
        contracts=stats_data["contracts"],
        equipments=stats_data["equipments"],
        orders=stats_data["orders"],
        issues=stats_data["issues"],
        reports=stats_data["reports"],
        quick_stats=quick_stats,
        recent_activities=activities
    )