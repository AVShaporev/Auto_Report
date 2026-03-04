from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import date

from model.user import User
from schema.contract import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractListResponse,
    ContractOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import contract as contract_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/contract", tags=["contract"])

@router.get("/list", response_model=PaginatedResponse[ContractListResponse])
async def get_contract_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по номеру или предмету"),
    spec_contract_id: Optional[int] = Query(None, ge=1, description="Фильтр по типу контракта"),
    customer_id: Optional[int] = Query(None, ge=1, description="Фильтр по заказчику"),
    executor_id: Optional[int] = Query(None, ge=1, description="Фильтр по подрядчику"),
    date_from: Optional[date] = Query(None, description="Дата заключения с"),
    date_to: Optional[date] = Query(None, description="Дата заключения по"),
    type_contract: Optional[str] = Query(None, description="Фильтр по типу"),
    sort_by: str = Query("number", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список контрактов с пагинацией
    
    Требуется право: contract_read
    """
    items, total = await contract_service.get_contracts_paginated_with_stats(
        pagination=pagination,
        current_user=current_user,
        search=search,
        spec_contract_id=spec_contract_id,
        customer_id=customer_id,
        executor_id=executor_id,
        date_from=date_from,
        date_to=date_to,
        type_contract=type_contract,
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

@router.get("/options", response_model=List[ContractOptionResponse])
async def get_contract_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список контрактов для выпадающих списков
    
    Требуется право: contract_read
    """
    contracts = await contract_service.get_contract_options(current_user)
    
    return [
        {
            "id": item.id,
            "number": item.number,
            "short_subject": item.short_subject
        }
        for item in contracts
    ]

@router.get("/all", response_model=List[ContractListResponse])
async def get_all_contracts(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все контракты (без пагинации)
    
    Требуется право: contract_read
    """
    contracts = await contract_service.get_all_contracts(
        current_user,
        load_relations=True
    )
    
    return [
        {
            "id": item.id,
            "number": item.number,
            "date_of_consclusion": item.date_of_consclusion,
            "date_of_completion": item.date_of_completion,
            "summ": item.summ,
            "short_subject": item.short_subject,
            "type_contract": item.type_contract,
            "spec_contract_name": item.spec_contract.name if item.spec_contract else None,
            "customer_name": item.customer.name if item.customer else None,
            "executor_name": item.executor.name if item.executor else None,
            "objects_count": len(item.objects) if item.objects else 0
        }
        for item in contracts
    ]

@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract_by_id(
    contract_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить контракт по ID
    
    Требуется право: contract_read
    """
    # Используем функцию со статистикой
    result = await contract_service.get_contract_with_stats(
        contract_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=ContractResponse)
async def create_contract(
    contract_data: ContractCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый контракт
    
    Требуется право: contract_create
    """
    contract = await contract_service.create_contract(
        contract_data,
        current_user
    )
    
    return {
        "id": contract.id,
        "number": contract.number,
        "date_of_consclusion": contract.date_of_consclusion,
        "date_of_completion": contract.date_of_completion,
        "summ": contract.summ,
        "subject": contract.subject,
        "short_subject": contract.short_subject,
        "type_contract": contract.type_contract,
        "spec_contract_id": contract.spec_contract_id,
        "customer_id": contract.customer_id,
        "executor_id": contract.executor_id,
        "spec_contract_name": None,
        "customer_name": None,
        "executor_name": None,
        "sub_contracts_count": 0,
        "objects_count": 0,
        "reports_count": 0,
        "orders_count": 0
    }

@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: int,
    contract_data: ContractUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить контракт
    
    Требуется право: contract_modify
    """
    contract = await contract_service.update_contract(
        contract_id,
        contract_data,
        current_user
    )
    
    # Получаем статистику для ответа
    async with contract_service.new_session() as session:
        sub_contracts_count = await contract_service.contract_data.count_sub_contracts(
            session, 
            contract_id
        )
        objects_count = await contract_service.contract_data.count_objects(
            session, 
            contract_id
        )
        reports_count = await contract_service.contract_data.count_reports(
            session, 
            contract_id
        )
        orders_count = await contract_service.contract_data.count_orders(
            session, 
            contract_id
        )
    
    return {
        "id": contract.id,
        "number": contract.number,
        "date_of_consclusion": contract.date_of_consclusion,
        "date_of_completion": contract.date_of_completion,
        "summ": contract.summ,
        "subject": contract.subject,
        "short_subject": contract.short_subject,
        "type_contract": contract.type_contract,
        "spec_contract_id": contract.spec_contract_id,
        "customer_id": contract.customer_id,
        "executor_id": contract.executor_id,
        "spec_contract_name": contract.spec_contract.name if contract.spec_contract else None,
        "customer_name": contract.customer.name if contract.customer else None,
        "executor_name": contract.executor.name if contract.executor else None,
        "sub_contracts_count": sub_contracts_count,
        "objects_count": objects_count,
        "reports_count": reports_count,
        "orders_count": orders_count
    }

@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить контракт
    
    Требуется право: contract_delete
    """
    await contract_service.delete_contract(
        contract_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Контракт с id {contract_id} успешно удален"
    }