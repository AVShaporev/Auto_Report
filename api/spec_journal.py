from fastapi import APIRouter, Depends, Query, UploadFile, File
from typing import Optional, List

from model.user import User
from schema.spec_journal import (
    SpecJournalCreate,
    SpecJournalUpdate,
    SpecJournalResponse,
    SpecJournalListResponse,
    SpecJournalOptionResponse,
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_journal as spec_journal_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_journal", tags=["spec_journal"])


@router.get("/list", response_model=PaginatedResponse[SpecJournalListResponse])
async def get_spec_journal_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию или краткому наименованию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
):
    """Получить список типов журналов с пагинацией. Требуется право: spec_journal_read."""
    items, total = await spec_journal_service.get_spec_journals_paginated(
        pagination=pagination,
        current_user=current_user,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    pages = (total + pagination.limit - 1) // pagination.limit

    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages,
    )


@router.get("/options", response_model=List[SpecJournalOptionResponse])
async def get_spec_journal_options(
    current_user: User = Depends(get_current_active_user),
):
    """Получить список типов журналов для выпадающих списков. Требуется право: spec_journal_read."""
    spec_journals = await spec_journal_service.get_spec_journal_options(current_user)
    return [
        {
            "id": item.id,
            "name": item.name,
            "short_name": item.short_name,
            "code": item.code,
        }
        for item in spec_journals
    ]


@router.get("/all", response_model=List[SpecJournalListResponse])
async def get_all_spec_journals(
    current_user: User = Depends(get_current_active_user),
):
    """Получить все типы журналов (без пагинации). Требуется право: spec_journal_read."""
    return await spec_journal_service.get_all_spec_journals(current_user)


@router.get("/{spec_journal_id}", response_model=SpecJournalResponse)
async def get_spec_journal_by_id(
    spec_journal_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Получить тип журнала по ID. Требуется право: spec_journal_read."""
    return await spec_journal_service.get_spec_journal_by_id(spec_journal_id, current_user)


@router.post("/create", response_model=SpecJournalResponse)
async def create_spec_journal(
    spec_journal_data: SpecJournalCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Создать новый тип журнала. Требуется право: spec_journal_create."""
    return await spec_journal_service.create_spec_journal(spec_journal_data, current_user)


@router.put("/{spec_journal_id}", response_model=SpecJournalResponse)
async def update_spec_journal(
    spec_journal_id: int,
    spec_journal_data: SpecJournalUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Обновить тип журнала. Требуется право: spec_journal_modify."""
    return await spec_journal_service.update_spec_journal(spec_journal_id, spec_journal_data, current_user)


@router.delete("/{spec_journal_id}")
async def delete_spec_journal(
    spec_journal_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Удалить тип журнала. Требуется право: spec_journal_delete."""
    await spec_journal_service.delete_spec_journal(spec_journal_id, current_user)
    return {
        "status": "success",
        "message": f"Тип журнала с id {spec_journal_id} успешно удалён",
    }


# ========== ШАБЛОН ДОКУМЕНТА ==========

@router.get("/{spec_journal_id}/template/info")
async def get_spec_journal_template_info(
    spec_journal_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить метаданные привязанного шаблона документа.
    Требуется право: spec_journal_read.
    """
    return await spec_journal_service.get_spec_journal_template_info(spec_journal_id, current_user)


@router.post("/{spec_journal_id}/template")
async def upload_spec_journal_template(
    spec_journal_id: int,
    file: UploadFile = File(..., description="Файл шаблона .docx или .dotx"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Загрузить новый шаблон документа для типа журнала (заменяет старый).
    Требуется право: spec_journal_modify. Лимит: 10 МБ. Расширения: .docx, .dotx.
    """
    return await spec_journal_service.upload_spec_journal_template(spec_journal_id, file, current_user)


@router.delete("/{spec_journal_id}/template")
async def delete_spec_journal_template(
    spec_journal_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Снять привязку шаблона и удалить файл с диска.
    Требуется право: spec_journal_modify.
    """
    return await spec_journal_service.delete_spec_journal_template(spec_journal_id, current_user)
