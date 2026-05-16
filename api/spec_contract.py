from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.spec_contract import (
    SpecContractCreate,
    SpecContractUpdate,
    SpecContractResponse,
    SpecContractListResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_contract as spec_contract_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_contract", tags=["spec_contract"])

@router.get("/list", response_model=PaginatedResponse[SpecContractListResponse])
async def get_spec_contract_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов договоров с пагинацией
    
    Требуется право: spec_contract_read
    """
    items, total = await spec_contract_service.get_spec_contracts_paginated_with_stats(
        pagination=pagination,
        current_user=current_user,
        search=search,
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

@router.get("/all", response_model=List[SpecContractListResponse])
async def get_all_spec_contracts(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все типы договоров (без пагинации)
    
    Требуется право: spec_contract_read
    """
    items = await spec_contract_service.get_all_spec_contracts(
        current_user,
        load_contracts=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "contracts_count": len(item.contracts) if item.contracts else 0
        }
        for item in items
    ]

@router.get("/{spec_contract_id}", response_model=SpecContractResponse)
async def get_spec_contract_by_id(
    spec_contract_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить тип договора по ID
    
    Требуется право: spec_contract_read
    """
    return await spec_contract_service.get_spec_contract_with_stats(
        spec_contract_id,
        current_user
    )

@router.post("/create", response_model=SpecContractResponse)
async def create_spec_contract(
    spec_contract_data: SpecContractCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый тип договора
    
    Требуется право: spec_contract_create
    """
    spec_contract = await spec_contract_service.create_spec_contract(
        spec_contract_data,
        current_user
    )
    
    return {
        "id": spec_contract.id,
        "name": spec_contract.name,
        "contracts_count": 0
    }

@router.put("/{spec_contract_id}", response_model=SpecContractResponse)
async def update_spec_contract(
    spec_contract_id: int,
    spec_contract_data: SpecContractUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить тип договора
    
    Требуется право: spec_contract_modify
    """
    return await spec_contract_service.update_spec_contract_with_stats(
        spec_contract_id,
        spec_contract_data,
        current_user
    )

@router.delete("/{spec_contract_id}")
async def delete_spec_contract(
    spec_contract_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить тип договора
    
    Требуется право: spec_contract_delete
    """
    await spec_contract_service.delete_spec_contract(
        spec_contract_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Тип договора с id {spec_contract_id} успешно удален"
    }