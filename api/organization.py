from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from model.user import User
from schema.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationListResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import organization as org_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/organization", tags=["organization"])

@router.get("/executor/list", response_model=PaginatedResponse[OrganizationListResponse])
async def get_organization_executor_list(
                                        pagination: PaginationParams = Depends(),
                                        search: Optional[str] = Query(None, description="Поиск по названию, ИНН"),
                                        customer: Optional[bool] = Query(None, description="Только заказчики"),
                                        executor: Optional[bool] = Query(None, description="Только подрядчики"),
                                        region_id: Optional[int] = Query(None, ge=1, description="Фильтр по региону"),
                                        bank_id: Optional[int] = Query(None, ge=1, description="Фильтр по банку"),
                                        sort_by: str = Query("name", description="Поле сортировки"),
                                        sort_order: str = Query("asc", regex="^(asc|desc)$"),
                                        current_user: User = Depends(get_current_active_user)
                                        ):
    """
    Получить список организаций с пагинацией
    
    Требуется право: organization_read
    """
    organizations, total = await org_service.get_organizations_executor_paginated(
                                                                                    pagination=pagination,
                                                                                    current_user=current_user,
                                                                                    search=search,
                                                                                    customer=customer,
                                                                                    executor=executor,
                                                                                    region_id=region_id,
                                                                                    bank_id=bank_id,
                                                                                    sort_by=sort_by,
                                                                                    sort_order=sort_order
                                                                                    )
    
    # Преобразуем в список для ответа
    items = []
    for org in organizations:
        items.append({
                        "id": org.id,
                        "name": org.name,
                        "short_name": org.short_name,
                        "inn": org.inn,
                        "customer": org.customer,
                        "executor": org.executor,
                        "bank_name": org.bank.name if org.bank else None,
                        "region_name": org.region.name if org.region else None
                    })
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
                                items=items,
                                total=total,
                                page=pagination.page,
                                per_page=pagination.limit,
                                pages=pages
                                )

@router.get("/customer/list", response_model=PaginatedResponse[OrganizationListResponse])
async def get_organization_executor_list(
                                            pagination: PaginationParams = Depends(),
                                            search: Optional[str] = Query(None, description="Поиск по названию, ИНН"),
                                            customer: Optional[bool] = Query(None, description="Только заказчики"),
                                            executor: Optional[bool] = Query(None, description="Только подрядчики"),
                                            region_id: Optional[int] = Query(None, ge=1, description="Фильтр по региону"),
                                            bank_id: Optional[int] = Query(None, ge=1, description="Фильтр по банку"),
                                            sort_by: str = Query("name", description="Поле сортировки"),
                                            sort_order: str = Query("asc", regex="^(asc|desc)$"),
                                            current_user: User = Depends(get_current_active_user)
                                            ):
    """
    Получить список организаций с пагинацией
    
    Требуется право: organization_read
    """
    organizations, total = await org_service.get_organizations_customer_paginated(
                                                                                    pagination=pagination,
                                                                                    current_user=current_user,
                                                                                    search=search,
                                                                                    customer=customer,
                                                                                    executor=executor,
                                                                                    region_id=region_id,
                                                                                    bank_id=bank_id,
                                                                                    sort_by=sort_by,
                                                                                    sort_order=sort_order
                                                                                    )
    
    # Преобразуем в список для ответа
    items = []
    for org in organizations:
        items.append({
                        "id": org.id,
                        "name": org.name,
                        "short_name": org.short_name,
                        "inn": org.inn,
                        "customer": org.customer,
                        "executor": org.executor,
                        "bank_name": org.bank.name if org.bank else None,
                        "region_name": org.region.name if org.region else None
                    })
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
                                items=items,
                                total=total,
                                page=pagination.page,
                                per_page=pagination.limit,
                                pages=pages
                            )

@router.get("/list", response_model=PaginatedResponse[OrganizationListResponse])
async def get_organization_list(
                                pagination: PaginationParams = Depends(),
                                search: Optional[str] = Query(None, description="Поиск по названию, ИНН"),
                                customer: Optional[bool] = Query(None, description="Только заказчики"),
                                executor: Optional[bool] = Query(None, description="Только подрядчики"),
                                region_id: Optional[int] = Query(None, ge=1, description="Фильтр по региону"),
                                bank_id: Optional[int] = Query(None, ge=1, description="Фильтр по банку"),
                                sort_by: str = Query("name", description="Поле сортировки"),
                                sort_order: str = Query("asc", regex="^(asc|desc)$"),
                                current_user: User = Depends(get_current_active_user)
                                ):
    """
    Получить список организаций с пагинацией
    
    Требуется право: organization_read
    """
    organizations, total = await org_service.get_organizations_paginated(
                                                                        pagination=pagination,
                                                                        current_user=current_user,
                                                                        search=search,
                                                                        customer=customer,
                                                                        executor=executor,
                                                                        region_id=region_id,
                                                                        bank_id=bank_id,
                                                                        sort_by=sort_by,
                                                                        sort_order=sort_order
                                                                        )
    
    # Преобразуем в список для ответа
    items = []
    for org in organizations:
        items.append({
                    "id": org.id,
                    "name": org.name,
                    "short_name": org.short_name,
                    "inn": org.inn,
                    "customer": org.customer,
                    "executor": org.executor,
                    "bank_name": org.bank.name if org.bank else None,
                    "region_name": org.region.name if org.region else None
                    })
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
                            items=items,
                            total=total,
                            page=pagination.page,
                            per_page=pagination.limit,
                            pages=pages
                            )

@router.get("/all", response_model=List[OrganizationListResponse])
async def get_all_organizations(
                                current_user: User = Depends(get_current_active_user)
                                ):
    """
    Получить все организации (без пагинации)
    
    Требуется право: organization_read
    """
    organizations = await org_service.get_all_organizations(
                                                            current_user,
                                                            load_relations = False)
    
    return organizations

@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization_by_id(
                                organization_id: int,
                                current_user: User = Depends(get_current_active_user)
                                ):
    """
    Получить организацию по ID
    
    Требуется право: organization_read
    """
    organization = await org_service.get_organization_by_id(
                                                            organization_id,
                                                            current_user,
                                                            load_relations=True
                                                            )
    
    # Преобразуем в dict для ответа
    org_dict = {
        "id": organization.id,
        "name": organization.name,
        "short_name": organization.short_name,
        "inn": organization.inn,
        "kpp": organization.kpp,
        "director_first_name": organization.director_first_name,
        "drector_last_name": organization.drector_last_name,
        "drector_surname": organization.drector_surname,
        "email": organization.email,
        "telephone": organization.telephone,
        "site": organization.site,
        "corr_check": organization.corr_check,
        "acc_check": organization.acc_check,
        "pers_check": organization.pers_check,
        "build_number": organization.build_number,
        "room_number": organization.room_number,
        "postal_code": organization.postal_code,
        "customer": organization.customer,
        "executor": organization.executor,
        "bank_id": organization.bank_id,
        "region_id": organization.region_id,
        "arial_id": organization.arial_id,
        "locality_id": organization.locality_id,
        "street_id": organization.street_id,
        "spec_build_id": organization.spec_build_id,
        "spec_room_id": organization.spec_room_id,
        "spec_job_title_id": organization.spec_job_title_id,
        # Связанные объекты
        "bank": {"id": organization.bank.id, "name": organization.bank.name} if organization.bank else None,
        "region": {"id": organization.region.id, "name": organization.region.name} if organization.region else None,
        "arial": {"id": organization.arial.id, "name": organization.arial.name} if organization.arial else None,
        "locality": {"id": organization.locality.id, "name": organization.locality.name} if organization.locality else None,
        "street": {"id": organization.street.id, "name": organization.street.name} if organization.street else None,
        "spec_build": {"id": organization.spec_build.id, "name": organization.spec_build.name} if organization.spec_build else None,
        "spec_room": {"id": organization.spec_room.id, "name": organization.spec_room.name} if organization.spec_room else None,
        "spec_job_title": {"id": organization.spec_job_title.id, "name": organization.spec_job_title.name} if organization.spec_job_title else None
    }
    
    return org_dict

@router.post("/create", response_model=OrganizationResponse)
async def create_organization(
    organization_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новую организацию
    
    Требуется право: organization_create
    """
    organization = await org_service.create_organization(
        organization_data,
        current_user
    )
    
    # Формируем ответ (аналогично get_by_id)
    org_dict = {
        "id": organization.id,
        "name": organization.name,
        "short_name": organization.short_name,
        "inn": organization.inn,
        "kpp": organization.kpp,
        "director_first_name": organization.director_first_name,
        "drector_last_name": organization.drector_last_name,
        "drector_surname": organization.drector_surname,
        "email": organization.email,
        "telephone": organization.telephone,
        "site": organization.site,
        "corr_check": organization.corr_check,
        "acc_check": organization.acc_check,
        "pers_check": organization.pers_check,
        "build_number": organization.build_number,
        "room_number": organization.room_number,
        "postal_code": organization.postal_code,
        "customer": organization.customer,
        "executor": organization.executor,
        "bank_id": organization.bank_id,
        "region_id": organization.region_id,
        "arial_id": organization.arial_id,
        "locality_id": organization.locality_id,
        "street_id": organization.street_id,
        "spec_build_id": organization.spec_build_id,
        "spec_room_id": organization.spec_room_id,
        "spec_job_title_id": organization.spec_job_title_id,
        "bank": {"id": organization.bank.id, "name": organization.bank.name} if organization.bank else None,
        "region": {"id": organization.region.id, "name": organization.region.name} if organization.region else None,
        "arial": {"id": organization.arial.id, "name": organization.arial.name} if organization.arial else None,
        "locality": {"id": organization.locality.id, "name": organization.locality.name} if organization.locality else None,
        "street": {"id": organization.street.id, "name": organization.street.name} if organization.street else None,
        "spec_build": {"id": organization.spec_build.id, "name": organization.spec_build.name} if organization.spec_build else None,
        "spec_room": {"id": organization.spec_room.id, "name": organization.spec_room.name} if organization.spec_room else None,
        "spec_job_title": {"id": organization.spec_job_title.id, "name": organization.spec_job_title.name} if organization.spec_job_title else None
    }
    
    return org_dict

@router.post("/customer/create", response_model=OrganizationResponse)
async def create_organization(
    organization_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новую организацию
    
    Требуется право: organization_create
    """
    organization = await org_service.create_organization(
        organization_data,
        current_user
    )
    
    # Формируем ответ (аналогично get_by_id)
    org_dict = {
        "id": organization.id,
        "name": organization.name,
        "short_name": organization.short_name,
        "inn": organization.inn,
        "kpp": organization.kpp,
        "director_first_name": organization.director_first_name,
        "drector_last_name": organization.drector_last_name,
        "drector_surname": organization.drector_surname,
        "email": organization.email,
        "telephone": organization.telephone,
        "site": organization.site,
        "corr_check": organization.corr_check,
        "acc_check": organization.acc_check,
        "pers_check": organization.pers_check,
        "build_number": organization.build_number,
        "room_number": organization.room_number,
        "postal_code": organization.postal_code,
        "customer": organization.customer,
        "executor": organization.executor,
        "bank_id": organization.bank_id,
        "region_id": organization.region_id,
        "arial_id": organization.arial_id,
        "locality_id": organization.locality_id,
        "street_id": organization.street_id,
        "spec_build_id": organization.spec_build_id,
        "spec_room_id": organization.spec_room_id,
        "spec_job_title_id": organization.spec_job_title_id,
        "bank": {"id": organization.bank.id, "name": organization.bank.name} if organization.bank else None,
        "region": {"id": organization.region.id, "name": organization.region.name} if organization.region else None,
        "arial": {"id": organization.arial.id, "name": organization.arial.name} if organization.arial else None,
        "locality": {"id": organization.locality.id, "name": organization.locality.name} if organization.locality else None,
        "street": {"id": organization.street.id, "name": organization.street.name} if organization.street else None,
        "spec_build": {"id": organization.spec_build.id, "name": organization.spec_build.name} if organization.spec_build else None,
        "spec_room": {"id": organization.spec_room.id, "name": organization.spec_room.name} if organization.spec_room else None,
        "spec_job_title": {"id": organization.spec_job_title.id, "name": organization.spec_job_title.name} if organization.spec_job_title else None
    }
    
    return org_dict

@router.post("/executor/create", response_model=OrganizationResponse)
async def create_organization(
    organization_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новую организацию
    
    Требуется право: organization_create
    """
    organization = await org_service.create_organization(
        organization_data,
        current_user
    )
    
    # Формируем ответ (аналогично get_by_id)
    org_dict = {
        "id": organization.id,
        "name": organization.name,
        "short_name": organization.short_name,
        "inn": organization.inn,
        "kpp": organization.kpp,
        "director_first_name": organization.director_first_name,
        "drector_last_name": organization.drector_last_name,
        "drector_surname": organization.drector_surname,
        "email": organization.email,
        "telephone": organization.telephone,
        "site": organization.site,
        "corr_check": organization.corr_check,
        "acc_check": organization.acc_check,
        "pers_check": organization.pers_check,
        "build_number": organization.build_number,
        "room_number": organization.room_number,
        "postal_code": organization.postal_code,
        "customer": organization.customer,
        "executor": organization.executor,
        "bank_id": organization.bank_id,
        "region_id": organization.region_id,
        "arial_id": organization.arial_id,
        "locality_id": organization.locality_id,
        "street_id": organization.street_id,
        "spec_build_id": organization.spec_build_id,
        "spec_room_id": organization.spec_room_id,
        "spec_job_title_id": organization.spec_job_title_id,
        "bank": {"id": organization.bank.id, "name": organization.bank.name} if organization.bank else None,
        "region": {"id": organization.region.id, "name": organization.region.name} if organization.region else None,
        "arial": {"id": organization.arial.id, "name": organization.arial.name} if organization.arial else None,
        "locality": {"id": organization.locality.id, "name": organization.locality.name} if organization.locality else None,
        "street": {"id": organization.street.id, "name": organization.street.name} if organization.street else None,
        "spec_build": {"id": organization.spec_build.id, "name": organization.spec_build.name} if organization.spec_build else None,
        "spec_room": {"id": organization.spec_room.id, "name": organization.spec_room.name} if organization.spec_room else None,
        "spec_job_title": {"id": organization.spec_job_title.id, "name": organization.spec_job_title.name} if organization.spec_job_title else None
    }
    
    return org_dict

@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: int,
    organization_data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить организацию
    
    Требуется право: organization_modify
    """
    organization = await org_service.update_organization(
        organization_id,
        organization_data,
        current_user
    )
    
    # Формируем ответ (аналогично get_by_id)
    org_dict = {
        "id": organization.id,
        "name": organization.name,
        "short_name": organization.short_name,
        "inn": organization.inn,
        "kpp": organization.kpp,
        "director_first_name": organization.director_first_name,
        "drector_last_name": organization.drector_last_name,
        "drector_surname": organization.drector_surname,
        "email": organization.email,
        "telephone": organization.telephone,
        "site": organization.site,
        "corr_check": organization.corr_check,
        "acc_check": organization.acc_check,
        "pers_check": organization.pers_check,
        "build_number": organization.build_number,
        "room_number": organization.room_number,
        "postal_code": organization.postal_code,
        "customer": organization.customer,
        "executor": organization.executor,
        "bank_id": organization.bank_id,
        "region_id": organization.region_id,
        "arial_id": organization.arial_id,
        "locality_id": organization.locality_id,
        "street_id": organization.street_id,
        "spec_build_id": organization.spec_build_id,
        "spec_room_id": organization.spec_room_id,
        "spec_job_title_id": organization.spec_job_title_id,
        "bank": {"id": organization.bank.id, "name": organization.bank.name} if organization.bank else None,
        "region": {"id": organization.region.id, "name": organization.region.name} if organization.region else None,
        "arial": {"id": organization.arial.id, "name": organization.arial.name} if organization.arial else None,
        "locality": {"id": organization.locality.id, "name": organization.locality.name} if organization.locality else None,
        "street": {"id": organization.street.id, "name": organization.street.name} if organization.street else None,
        "spec_build": {"id": organization.spec_build.id, "name": organization.spec_build.name} if organization.spec_build else None,
        "spec_room": {"id": organization.spec_room.id, "name": organization.spec_room.name} if organization.spec_room else None,
        "spec_job_title": {"id": organization.spec_job_title.id, "name": organization.spec_job_title.name} if organization.spec_job_title else None
    }
    
    return org_dict

@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить организацию
    
    Требуется право: organization_delete
    """
    success = await org_service.delete_organization(
        organization_id,
        current_user
    )
    
    return {
        "status": "success",
        "message": f"Организация с id {organization_id} успешно удалена"
    }