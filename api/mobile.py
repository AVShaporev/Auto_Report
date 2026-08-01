"""Mobile-компактные endpoints для PWA/Capacitor-клиента (Mobile M1.3).

Все под общим `/api/mobile/*`, все требуют Bearer JWT (существующий
get_current_user из service/auth.py).
"""
from typing import List

from fastapi import APIRouter, Depends, Query

from database.database import new_session
from data import mobile as mobile_data
from model.user import User
from schema.mobile import (
    MobileIssueListItem,
    MobileObjectSummaryItem,
    MobileOrderListItem,
    MobileReportListItem,
)
from service.auth import get_current_user


router = APIRouter(prefix="/api/mobile", tags=["mobile"])


@router.get("/issues", response_model=List[MobileIssueListItem])
async def mobile_issues(
    only_open: bool = Query(True, description="Только неустранённые"),
    only_mine: bool = Query(True, description="Только назначенные на меня"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
) -> List[MobileIssueListItem]:
    async with new_session() as session:
        rows = await mobile_data.get_issues_mobile_list(
            session,
            user_id=current_user.id,
            only_open=only_open,
            only_mine=only_mine,
            limit=limit,
        )
    return [MobileIssueListItem(**r) for r in rows]


@router.get("/objects", response_model=List[MobileObjectSummaryItem])
async def mobile_objects(
    contract_id: int | None = Query(None, description="Фильтр по контракту"),
    limit: int = Query(200, ge=1, le=500),
    current_user: User = Depends(get_current_user),
) -> List[MobileObjectSummaryItem]:
    async with new_session() as session:
        rows = await mobile_data.get_objects_mobile_summary(
            session, contract_id=contract_id, limit=limit,
        )
    return [MobileObjectSummaryItem(**r) for r in rows]


@router.get("/reports", response_model=List[MobileReportListItem])
async def mobile_reports(
    only_mine: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
) -> List[MobileReportListItem]:
    async with new_session() as session:
        rows = await mobile_data.get_reports_mobile_list(
            session,
            user_id=current_user.id,
            only_mine=only_mine,
            limit=limit,
        )
    return [MobileReportListItem(**r) for r in rows]


@router.get("/orders", response_model=List[MobileOrderListItem])
async def mobile_orders(
    only_mine: bool = Query(True),
    only_open: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
) -> List[MobileOrderListItem]:
    async with new_session() as session:
        rows = await mobile_data.get_orders_mobile_list(
            session,
            user_id=current_user.id,
            only_mine=only_mine,
            only_open=only_open,
            limit=limit,
        )
    return [MobileOrderListItem(**r) for r in rows]
