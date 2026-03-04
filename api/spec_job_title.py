from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_job_title import (
    SpecJobTitleCreate,
    SpecJobTitleUpdate,
    SpecJobTitleResponse,
    SpecJobTitleListResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_job_title as spec_job_title_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_job_title", tags=["spec_job_title"])

@router.get("/list", response_model=PaginatedResponse[SpecJobTitleListResponse])
async def get_spec_job_title_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список должностей руководителей с пагинацией
    
    Требуется право: spec_job_title_read
    """
    items, total = await spec_job_title_service.get_spec_job_titles_paginated_with_stats(
                                                                    pagination=pagination,
                                                                    current_user=current_user,
                                                                    search=search,
                                                                    sort_by=sort_by,
                                                                    sort_order=sort_order
                                                                )
                                                                
    # # Преобразуем в список для ответа
    # result_items = []
    # for item in items:

    #     # Получаем количество связанных организаций
    #     organizations_count = len(item.organizations) if item.organizations else 0
        
    #     result_items.append({
    #         "id": item.id,
    #         "name": item.name,
    #         "organizations_count": organizations_count
    #     })
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
                                items=items,
                                total=total,
                                page=pagination.page,
                                per_page=pagination.limit,
                                pages=pages
                                )

@router.get("/all", response_model=List[SpecJobTitleListResponse])
async def get_all_spec_job_titles(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все должности руководителей (без пагинации)
    
    Требуется право: spec_job_title_read
    """
    items = await spec_job_title_service.get_all_spec_job_titles(
        current_user,
        load_organizations=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "organizations_count": len(item.organizations) if item.organizations else 0
        }
        for item in items
    ]

@router.get("/{spec_job_title_id}", response_model=SpecJobTitleResponse)
async def get_spec_job_title_by_id(
                                    spec_job_title_id: int,
                                    current_user: User = Depends(get_current_active_user),
                                    load_organizations: bool = True
                                    ):
    """
    Получить должность руководителя по ID
    
    Требуется право: spec_job_title_read
    """
    spec_job_title = await spec_job_title_service.get_spec_job_title_with_stats(
        spec_job_title_id,
        current_user
    )
    
    # Формируем ответ
    return get_spec_job_title_with_stats

@router.post("/create", response_model=SpecJobTitleResponse)
async def create_spec_job_title(
    spec_job_title_data: SpecJobTitleCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новую должность руководителя
    
    Требуется право: spec_job_title_create
    """
    spec_job_title = await spec_job_title_service.create_spec_job_title(
        spec_job_title_data,
        current_user
    )
    
    return {
        "id": spec_job_title.id,
        "name": spec_job_title.name,
        "organizations_count": 0
    }

@router.put("/{spec_job_title_id}", response_model=SpecJobTitleResponse)
async def update_spec_job_title(
                                spec_job_title_id: int,
                                spec_job_title_data: SpecJobTitleUpdate,
                                current_user: User = Depends(get_current_active_user),
                                load_organizations: bool = True
                                ):
    """
    Обновить должность руководителя
    
    Требуется право: spec_job_title_modify
    """
    spec_job_title = await spec_job_title_service.update_spec_job_title(
        spec_job_title_id,
        spec_job_title_data,
        current_user
    )
    
    # Получаем количество связанных организаций
    try:
        organizations_count = len(spec_job_title.organizations)
    except:
        organizations_count = 0
    
    return {
            "id": spec_job_title.id,
            "name": spec_job_title.name,
            "organizations_count": organizations_count
            }

@router.delete("/{spec_job_title_id}")
async def delete_spec_job_title(
    spec_job_title_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить должность руководителя
    
    Требуется право: spec_job_title_delete
    """
    await spec_job_title_service.delete_spec_job_title(
        spec_job_title_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Должность руководителя с id {spec_job_title_id} успешно удалена"
    }