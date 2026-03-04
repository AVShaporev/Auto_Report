from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from model.user import User
from schema.bank import (
    BankCreate,
    BankUpdate,
    BankResponse,
    BankListResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import bank as bank_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/bank", tags=["bank"])

@router.get("/list", response_model=PaginatedResponse[BankListResponse])
async def get_bank_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию, БИК или ИНН"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список банков с пагинацией
    
    Требуется право: bank_read
    """
    items, total = await bank_service.get_banks_paginated_with_stats(
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

@router.get("/all", response_model=List[BankListResponse])
async def get_all_banks(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все банки (без пагинации)
    
    Требуется право: bank_read
    """
    banks = await bank_service.get_all_banks(
        current_user,
        load_organizations=True
    )
    
    return [
        {
            "id": bank.id,
            "name": bank.name,
            "bik": bank.bik,
            "inn": bank.inn,
            "organizations_count": len(bank.organizations) if bank.organizations else 0
        }
        for bank in banks
    ]

@router.get("/{bank_id}", response_model=BankResponse)
async def get_bank_by_id(
    bank_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить банк по ID
    
    Требуется право: bank_read
    """
    # Используем функцию со статистикой
    result = await bank_service.get_bank_with_stats(
        bank_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=BankResponse)
async def create_bank(
    bank_data: BankCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый банк
    
    Требуется право: bank_create
    """
    bank = await bank_service.create_bank(
        bank_data,
        current_user
    )
    
    return {
        "id": bank.id,
        "name": bank.name,
        "bik": bank.bik,
        "inn": bank.inn,
        "organizations_count": 0
    }

@router.put("/{bank_id}", response_model=BankResponse)
async def update_bank(
    bank_id: int,
    bank_data: BankUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить банк
    
    Требуется право: bank_modify
    """
    bank = await bank_service.update_bank(
        bank_id,
        bank_data,
        current_user
    )
    
    # Получаем количество связанных организаций
    async with bank_service.new_session() as session:
        organizations_count = await bank_service.bank_data.count_organizations(
            session, 
            bank_id
        )
    
    return {
        "id": bank.id,
        "name": bank.name,
        "bik": bank.bik,
        "inn": bank.inn,
        "organizations_count": organizations_count
    }

@router.delete("/{bank_id}")
async def delete_bank(
    bank_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить банк
    
    Требуется право: bank_delete
    """
    await bank_service.delete_bank(
        bank_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Банк с id {bank_id} успешно удален"
    }

# Дополнительный эндпоинт для поиска по БИК
@router.get("/by-bik/{bik}", response_model=BankResponse)
async def get_bank_by_bik(
    bik: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить банк по БИК
    
    Требуется право: bank_read
    """
    await bank_service.check_permission(current_user, "bank_read", "просмотра банков")
    
    async with bank_service.new_session() as session:
        bank = await bank_service.bank_data.get_by_bik(session, bik)
        
        if not bank:
            raise HTTPException(
                status_code=404,
                detail=f"Банк с БИК '{bik}' не найден"
            )
        
        organizations_count = await bank_service.bank_data.count_organizations(
            session, 
            bank.id
        )
        
        return {
            "id": bank.id,
            "name": bank.name,
            "bik": bank.bik,
            "inn": bank.inn,
            "organizations_count": organizations_count
        }