from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, List, Any

from utils.timer import timer



@timer
async def get_dashboard_stats(session: AsyncSession) -> Dict[str, Any]:
    """
    Получить общую статистику для дашборда одним запросом.
    Возвращает словарь со счётчиками и быстрой статистикой.
    """
    query = text("""
        SELECT 
            (SELECT COUNT(*) FROM objects) as objects,
            (SELECT COUNT(*) FROM contracts) as contracts,
            (SELECT COUNT(*) FROM equipments) as equipments,
            (SELECT COUNT(*) FROM orders) as orders,
            (SELECT COUNT(*) FROM issues) as issues,
            (SELECT COUNT(*) FROM reports) as reports,
            
            (SELECT COUNT(*) FROM orders WHERE status = 'pending') as pending_orders,
            (SELECT COUNT(*) FROM issues WHERE is_resolved = false) as unresolved_issues,
            (SELECT COUNT(*) FROM issues WHERE is_critical = true AND is_resolved = false) as critical_issues
    """)
    result = await session.execute(query)
    row = result.fetchone()
    # Преобразуем Row в словарь (работает для SQLAlchemy 1.4+)
    return dict(row._mapping)

@timer
async def get_recent_activities(session: AsyncSession, limit: int = 10) -> List[Dict]:
    """
    Получить последние активности (созданные записи) из разных таблиц.
    Возвращает список словарей с полями: type, id, title, created_at.
    """
    query = text("""
        (SELECT 
            'object' as type,
            id,
            name as title,
            created_at
        FROM objects 
        ORDER BY created_at DESC 
        LIMIT 3)
        UNION ALL
        (SELECT 
            'contract' as type,
            id,
            number as title,
            created_at
        FROM contracts 
        ORDER BY created_at DESC 
        LIMIT 3)
        UNION ALL
        (SELECT 
            'order' as type,
            id,
            number as title,
            created_at
        FROM orders 
        ORDER BY created_at DESC 
        LIMIT 3)
        UNION ALL
        (SELECT 
            'issue' as type,
            id,
            title,
            created_at
        FROM issues 
        ORDER BY created_at DESC 
        LIMIT 3)
        ORDER BY created_at DESC 
        LIMIT :limit
    """)
    result = await session.execute(query, {"limit": limit})
    rows = result.fetchall()
    activities = []
    for row in rows:
        activities.append({
            "id": row.id,
            "type": row.type,
            "title": row.title,
            "created_at": row.created_at
        })
    return activities

@timer
async def get_dashboard_spec_stats(session: AsyncSession) -> Dict[str, Any]:
    """
    Получить общую статистику для справочников одним запросом.
    Возвращает словарь со счётчиками.
    """
    query = text("""
        SELECT 
            (SELECT COUNT(*) FROM spec_regions) as spec_regions,
            (SELECT COUNT(*) FROM spec_arials) as spec_arials,
            (SELECT COUNT(*) FROM spec_localitys) as spec_localitys,
            (SELECT COUNT(*) FROM spec_streets) as spec_streets,
            (SELECT COUNT(*) FROM spec_builds) as spec_builds,
            (SELECT COUNT(*) FROM spec_rooms) as spec_rooms,
            
            (SELECT COUNT(*) FROM spec_contracts) as spec_contracts,
            (SELECT COUNT(*) FROM spec_job_titles) as spec_job_titles,

            (SELECT COUNT(*) FROM spec_equipments) as spec_equipments,
            (SELECT COUNT(*) FROM spec_orders) as spec_orders,
            (SELECT COUNT(*) FROM spec_systems) as spec_systems,
            (SELECT COUNT(*) FROM operations) as operations,
            (SELECT COUNT(*) FROM periods) as periods
    """)
    result = await session.execute(query)
    row = result.fetchone()
    # Преобразуем Row в словарь (работает для SQLAlchemy 1.4+)
    return dict(row._mapping)