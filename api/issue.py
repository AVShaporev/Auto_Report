from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import date

from model.user import User
from schema.issue import (
    IssueCreate,
    IssueUpdate,
    IssueStatusUpdate,
    IssueResponse,
    IssueListResponse,
    IssueOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import issue as issue_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/issue", tags=["issue"])

@router.get("/list", response_model=PaginatedResponse[IssueListResponse])
async def get_issue_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по номеру или заголовку"),
    object_id: Optional[int] = Query(None, ge=1, description="Фильтр по объекту"),
    equipment_id: Optional[int] = Query(None, ge=1, description="Фильтр по оборудованию"),
    contract_id: Optional[int] = Query(None, ge=1, description="Фильтр по договору"),
    status_id: Optional[int] = Query(None, ge=1, description="Фильтр по статусу (ID из справочника)"),
    priority_id: Optional[int] = Query(None, ge=1, description="Фильтр по приоритету (ID из справочника)"),
    is_resolved: Optional[bool] = Query(None, description="Только устраненные/неустраненные"),
    is_critical: Optional[bool] = Query(None, description="Только критические"),
    reported_by_id: Optional[int] = Query(None, ge=1, description="Фильтр по создателю"),
    assigned_to_id: Optional[int] = Query(None, ge=1, description="Фильтр по ответственному"),
    date_from: Optional[date] = Query(None, description="Дата обнаружения с"),
    date_to: Optional[date] = Query(None, description="Дата обнаружения по"),
    sort_by: str = Query("detected_date", description="Поле сортировки"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список неисправностей с пагинацией
    
    Требуется право: issue_read
    """
    items, total = await issue_service.get_issues_paginated_with_details(
        pagination=pagination,
        current_user=current_user,
        search=search,
        object_id=object_id,
        equipment_id=equipment_id,
        contract_id=contract_id,
        status_id=status_id,
        priority_id=priority_id,
        is_resolved=is_resolved,
        is_critical=is_critical,
        reported_by_id=reported_by_id,
        assigned_to_id=assigned_to_id,
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

@router.get("/my", response_model=PaginatedResponse[IssueListResponse])
async def get_my_issues(
    pagination: PaginationParams = Depends(),
    status_id: Optional[int] = Query(None, ge=1, description="Фильтр по статусу (ID из справочника)"),
    is_resolved: Optional[bool] = Query(None, description="Только устраненные/неустраненные"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список своих неисправностей (сообщенных текущим пользователем)
    
    Требуется право: issue_read
    """
    items, total = await issue_service.get_issues_by_current_user(
        pagination=pagination,
        current_user=current_user,
        status_id=status_id,
        is_resolved=is_resolved
    )
    
    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "number": item.number,
            "title": item.title,
            "status_id": item.status_id,
            "status_name": item.status.name if item.status else None,
            "status_code": item.status.code if item.status else None,
            "priority_id": item.priority_id,
            "priority_name": item.priority.name if item.priority else None,
            "priority_code": item.priority.code if item.priority else None,
            "detected_date": item.detected_date,
            "is_resolved": item.is_resolved,
            "is_critical": item.is_critical,
            "object_name": item.object.name if item.object else None,
            "equipment_name": item.equipment.name if item.equipment else None,
            "assigned_to_name": item.assigned_to.name if item.assigned_to else None
        })
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=result_items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages
    )

@router.get("/assigned", response_model=PaginatedResponse[IssueListResponse])
async def get_assigned_issues(
    pagination: PaginationParams = Depends(),
    status_id: Optional[int] = Query(None, ge=1, description="Фильтр по статусу (ID из справочника)"),
    is_resolved: Optional[bool] = Query(None, description="Только устраненные/неустраненные"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список неисправностей, назначенных текущему пользователю
    
    Требуется право: issue_read
    """
    items, total = await issue_service.get_issues_assigned_to_current_user(
        pagination=pagination,
        current_user=current_user,
        status_id=status_id,
        is_resolved=is_resolved
    )
    
    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "number": item.number,
            "title": item.title,
            "status_id": item.status_id,
            "status_name": item.status.name if item.status else None,
            "status_code": item.status.code if item.status else None,
            "priority_id": item.priority_id,
            "priority_name": item.priority.name if item.priority else None,
            "priority_code": item.priority.code if item.priority else None,
            "detected_date": item.detected_date,
            "is_resolved": item.is_resolved,
            "is_critical": item.is_critical,
            "object_name": item.object.name if item.object else None,
            "equipment_name": item.equipment.name if item.equipment else None,
            "reported_by_name": item.reported_by.name if item.reported_by else None
        })
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=result_items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages
    )

@router.get("/by-object/{object_id}", response_model=List[IssueListResponse])
async def get_issues_by_object(
    object_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все неисправности по объекту
    
    Требуется право: issue_read
    """
    issues = await issue_service.get_issues_by_object(object_id, current_user)

    return [
        {
            "id": item.id,
            "number": item.number,
            "title": item.title,
            "status_id": item.status_id,
            "status_name": item.status.name if item.status else None,
            "status_code": item.status.code if item.status else None,
            "priority_id": item.priority_id,
            "priority_name": item.priority.name if item.priority else None,
            "priority_code": item.priority.code if item.priority else None,
            "detected_date": item.detected_date,
            "resolved_date": item.resolved_date,
            "is_resolved": item.is_resolved,
            "is_critical": item.is_critical,
            "created_at": item.created_at,
            "object_id": item.object_equipment.object_id if item.object_equipment else None,
            "object_name": item.object_equipment.object.name if item.object_equipment and item.object_equipment.object else None,
            "equipment_id": item.object_equipment.equipment_id if item.object_equipment else None,
            "equipment_name": item.object_equipment.equipment.name if item.object_equipment and item.object_equipment.equipment else None,
        }
        for item in issues
    ]

@router.get("/by-equipment/{equipment_id}", response_model=List[IssueListResponse])
async def get_issues_by_equipment(
    equipment_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все неисправности по оборудованию
    
    Требуется право: issue_read
    """
    issues = await issue_service.get_issues_by_equipment(equipment_id, current_user)

    return [
        {
            "id": item.id,
            "number": item.number,
            "title": item.title,
            "status_id": item.status_id,
            "status_name": item.status.name if item.status else None,
            "status_code": item.status.code if item.status else None,
            "priority_id": item.priority_id,
            "priority_name": item.priority.name if item.priority else None,
            "priority_code": item.priority.code if item.priority else None,
            "detected_date": item.detected_date,
            "resolved_date": item.resolved_date,
            "is_resolved": item.is_resolved,
            "is_critical": item.is_critical,
            "created_at": item.created_at,
            "object_id": item.object_equipment.object_id if item.object_equipment else None,
            "object_name": item.object_equipment.object.name if item.object_equipment and item.object_equipment.object else None,
            "equipment_id": item.object_equipment.equipment_id if item.object_equipment else None,
            "equipment_name": item.object_equipment.equipment.name if item.object_equipment and item.object_equipment.equipment else None,
        }
        for item in issues
    ]

@router.get("/options", response_model=List[IssueOptionResponse])
async def get_issue_options(
    status_id: Optional[int] = Query(None, ge=1, description="Фильтр по статусу (ID из справочника)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список неисправностей для выпадающих списков

    Требуется право: issue_read
    """
    issues = await issue_service.get_issues_paginated(
        pagination=PaginationParams(page=1, per_page=100),
        current_user=current_user,
        status_id=status_id
    )

    return [
        {
            "id": item.id,
            "number": item.number,
            "title": item.title,
            "status_id": item.status_id,
            "status_code": item.status.code if item.status else None,
            "status_name": item.status.name if item.status else None,
            "priority_id": item.priority_id,
            "priority_name": item.priority.name if item.priority else None,
            "priority_code": item.priority.code if item.priority else None,
            "detected_date": item.detected_date,
            "is_resolved": item.is_resolved
        }
        for item in issues[0]
    ]

@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue_by_id(
    issue_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить неисправность по ID
    
    Требуется право: issue_read
    """
    result = await issue_service.get_issue_with_details(
        issue_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=IssueResponse)
async def create_issue(
    issue_data: IssueCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новую неисправность
    
    reported_by_id автоматически берется из текущего пользователя
    
    Требуется право: issue_create
    """
    issue = await issue_service.create_issue(
        issue_data,
        current_user
    )
    
    return await issue_service.get_issue_with_details(issue.id, current_user)

@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: int,
    issue_data: IssueUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить неисправность
    
    Требуется право: issue_modify
    """
    issue = await issue_service.update_issue(
        issue_id,
        issue_data,
        current_user
    )
    
    return await issue_service.get_issue_with_details(issue.id, current_user)

@router.patch("/{issue_id}/status", response_model=IssueResponse)
async def update_issue_status(
    issue_id: int,
    status_update: IssueStatusUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить статус неисправности
    
    Требуется право: issue_modify
    """
    issue = await issue_service.update_issue_status(
        issue_id,
        status_update,
        current_user
    )
    
    return await issue_service.get_issue_with_details(issue.id, current_user)

@router.patch("/{issue_id}/assign/{user_id}", response_model=IssueResponse)
async def assign_issue(
    issue_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Назначить ответственного за неисправность
    
    Требуется право: issue_modify
    """
    issue = await issue_service.assign_issue(
        issue_id,
        user_id,
        current_user
    )
    
    return await issue_service.get_issue_with_details(issue.id, current_user)

@router.delete("/{issue_id}")
async def delete_issue(
    issue_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить неисправность
    
    Требуется право: issue_delete
    """
    await issue_service.delete_issue(
        issue_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Неисправность с id {issue_id} успешно удалена"
    }