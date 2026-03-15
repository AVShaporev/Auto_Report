from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import date

from model.user import User
from schema.report import (
    ReportCreate,
    ReportUpdate,
    ReportApprove,
    ReportResponse,
    ReportListResponse,
    ReportOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import report as report_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/report", tags=["report"])

@router.get("/list", response_model=PaginatedResponse[ReportListResponse])
async def get_report_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по номеру или описанию"),
    period_id: Optional[int] = Query(None, ge=1, description="Фильтр по периоду"),
    contract_id: Optional[int] = Query(None, ge=1, description="Фильтр по контракту"),
    object_id: Optional[int] = Query(None, ge=1, description="Фильтр по объекту"),
    user_id: Optional[int] = Query(None, ge=1, description="Фильтр по пользователю"),
    check_pass: Optional[bool] = Query(None, description="Фильтр по утверждению"),
    date_from: Optional[date] = Query(None, description="Дата создания с"),
    date_to: Optional[date] = Query(None, description="Дата создания по"),
    sort_by: str = Query("created_at", description="Поле сортировки"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список отчетов с пагинацией
    
    Требуется право: report_read
    """
    items, total = await report_service.get_reports_paginated_with_details(
        pagination=pagination,
        current_user=current_user,
        search=search,
        period_id=period_id,
        contract_id=contract_id,
        object_id=object_id,
        user_id=user_id,
        check_pass=check_pass,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages
    )

@router.get("/my", response_model=PaginatedResponse[ReportListResponse])
async def get_my_reports(
    pagination: PaginationParams = Depends(),
    check_pass: Optional[bool] = Query(None, description="Фильтр по утверждению"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список своих отчетов
    
    Требуется право: report_read
    """
    items, total = await report_service.get_reports_by_current_user(
        pagination=pagination,
        current_user=current_user,
        check_pass=check_pass
    )
    
    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "number": item.number,
            "check_pass": item.check_pass,
            "created_at": item.created_at,
            "period_name": item.period.name if item.period else None,
            "contract_number": item.contract.number if item.contract else None,
            "object_name": item.object.name if item.object else None,
            "user_name": item.user.name if item.user else None
        })
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=result_items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages
    )

@router.get("/options", response_model=List[ReportOptionResponse])
async def get_report_options(
    check_pass: Optional[bool] = Query(None, description="Фильтр по утверждению"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список отчетов для выпадающих списков
    
    Требуется право: report_read
    """
    reports = await report_service.get_report_options(current_user, check_pass=check_pass)
    
    return [
        {
            "id": report.id,
            "number": report.number,
            "check_pass": report.check_pass
        }
        for report in reports
    ]

@router.get("/unapproved", response_model=List[ReportListResponse])
async def get_unapproved_reports(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список неутвержденных отчетов
    
    Требуется право: report_read
    """
    items, _ = await report_service.get_reports_paginated_with_details(
        pagination=PaginationParams(page=1, per_page=100),
        current_user=current_user,
        check_pass=False
    )
    
    return items

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report_by_id(
    report_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить отчет по ID
    
    Требуется право: report_read
    """
    result = await report_service.get_report_with_details(
        report_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=ReportResponse)
async def create_report(
    report_data: ReportCreate,  # 👈 user_id не передается
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый отчет
    
    user_id автоматически берется из текущего пользователя
    
    Требуется право: report_create
    """
    report = await report_service.create_report(
        report_data,
        current_user  # 👈 Передаем текущего пользователя
    )
    
    return await report_service.get_report_with_details(report.id, current_user)

@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: int,
    report_data: ReportUpdate,  # 👈 user_id нет в схеме
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить отчет
    
    Требуется право: report_modify
    """
    report = await report_service.update_report(
        report_id,
        report_data,
        current_user
    )
    
    return await report_service.get_report_with_details(report.id, current_user)

@router.patch("/{report_id}/approve", response_model=ReportResponse)
async def approve_report(
    report_id: int,
    approve_data: ReportApprove,
    current_user: User = Depends(get_current_active_user)
):
    """
    Утвердить или отклонить отчет
    
    Требуется право: report_modify
    """
    report = await report_service.approve_report(
        report_id,
        approve_data,
        current_user
    )
    
    return await report_service.get_report_with_details(report.id, current_user)

@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить отчет
    
    Требуется право: report_delete
    """
    await report_service.delete_report(
        report_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Отчет с id {report_id} успешно удален"
    }