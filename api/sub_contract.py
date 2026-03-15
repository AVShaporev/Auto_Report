from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import date

from model.user import User
from schema.sub_contract import (
    SubContractCreate,
    SubContractUpdate,
    SubContractResponse,
    SubContractListResponse,
    SubContractOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import sub_contract as sub_contract_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/sub_contract", tags=["sub_contract"])

@router.get("/list", response_model=PaginatedResponse[SubContractListResponse])
async def get_sub_contract_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по номеру или предмету"),
    contract_id: Optional[int] = Query(None, ge=1, description="Фильтр по контракту"),
    date_from: Optional[date] = Query(None, description="Дата заключения с"),
    date_to: Optional[date] = Query(None, description="Дата заключения по"),
    sort_by: str = Query("date_of_consclusion", description="Поле сортировки"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список дополнительных соглашений с пагинацией
    
    Требуется право: sub_contract_read
    """
    items, total = await sub_contract_service.get_sub_contracts_paginated_with_details(
        pagination=pagination,
        current_user=current_user,
        search=search,
        contract_id=contract_id,
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

@router.get("/options", response_model=List[SubContractOptionResponse])
async def get_sub_contract_options(
    contract_id: Optional[int] = Query(None, ge=1, description="Фильтр по контракту"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список дополнительных соглашений для выпадающих списков
    
    Требуется право: sub_contract_read
    """
    sub_contracts = await sub_contract_service.get_sub_contract_options(
        current_user, 
        contract_id=contract_id
    )
    
    return [
        {
            "id": item.id,
            "number": item.number,
            "subject": item.subject
        }
        for item in sub_contracts
    ]

@router.get("/by-contract/{contract_id}", response_model=List[SubContractListResponse])
async def get_sub_contracts_by_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все дополнительные соглашения по контракту
    
    Требуется право: sub_contract_read
    """
    return await sub_contract_service.get_sub_contracts_by_contract(
        contract_id,
        current_user
    )

@router.get("/{sub_contract_id}", response_model=SubContractResponse)
async def get_sub_contract_by_id(
    sub_contract_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить дополнительное соглашение по ID
    
    Требуется право: sub_contract_read
    """
    # Используем функцию с детальной информацией
    result = await sub_contract_service.get_sub_contract_with_details(
        sub_contract_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=SubContractResponse)
async def create_sub_contract(
    sub_contract_data: SubContractCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новое дополнительное соглашение
    
    Требуется право: sub_contract_create
    """
    sub_contract = await sub_contract_service.create_sub_contract(
        sub_contract_data,
        current_user
    )
    
    # Возвращаем полную информацию
    return await sub_contract_service.get_sub_contract_with_details(sub_contract.id, current_user)

@router.put("/{sub_contract_id}", response_model=SubContractResponse)
async def update_sub_contract(
    sub_contract_id: int,
    sub_contract_data: SubContractUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить дополнительное соглашение
    
    Требуется право: sub_contract_modify
    """
    sub_contract = await sub_contract_service.update_sub_contract(
        sub_contract_id,
        sub_contract_data,
        current_user
    )
    
    # Возвращаем полную информацию
    return await sub_contract_service.get_sub_contract_with_details(sub_contract.id, current_user)

@router.delete("/{sub_contract_id}")
async def delete_sub_contract(
    sub_contract_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить дополнительное соглашение
    
    Требуется право: sub_contract_delete
    """
    await sub_contract_service.delete_sub_contract(
        sub_contract_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Дополнительное соглашение с id {sub_contract_id} успешно удалено"
    }