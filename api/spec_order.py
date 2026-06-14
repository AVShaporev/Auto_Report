from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Response

from service.render_docx import build_attachment_headers
from typing import Optional, List

from model.user import User
from schema.spec_order import (
    SpecOrderCreate,
    SpecOrderUpdate,
    SpecOrderResponse,
    SpecOrderListResponse,
    SpecOrderOptionResponse
)
from schema.pagination import PaginationParams, PaginatedResponse
from service import spec_order as spec_order_service
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/api/spec_order", tags=["spec_order"])

@router.get("/list", response_model=PaginatedResponse[SpecOrderListResponse])
async def get_spec_order_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию или краткому наименованию"),
    sort_by: str = Query("name", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов заявок с пагинацией
    
    Требуется право: spec_order_read
    """
    items, total = await spec_order_service.get_spec_orders_paginated_with_stats(
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

@router.get("/options", response_model=List[SpecOrderOptionResponse])
async def get_spec_order_options(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список типов заявок для выпадающих списков
    
    Требуется право: spec_order_read
    """
    spec_orders = await spec_order_service.get_spec_order_options(current_user)
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "short_name": item.short_name
        }
        for item in spec_orders
    ]

@router.get("/all", response_model=List[SpecOrderListResponse])
async def get_all_spec_orders(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить все типы заявок (без пагинации)
    
    Требуется право: spec_order_read
    """
    spec_orders = await spec_order_service.get_all_spec_orders(
        current_user,
        load_orders=True
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "short_name": item.short_name,
            "is_system": item.is_system,
            "is_default_planned": item.is_default_planned,
            "is_default_primary": item.is_default_primary,
            "orders_count": len(item.orders) if item.orders else 0,
            "template_filename": item.template_filename,
        }
        for item in spec_orders
    ]

@router.get("/{spec_order_id}", response_model=SpecOrderResponse)
async def get_spec_order_by_id(
    spec_order_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить тип заявки по ID
    
    Требуется право: spec_order_read
    """
    # Используем функцию со статистикой
    result = await spec_order_service.get_spec_order_with_stats(
        spec_order_id,
        current_user
    )
    
    return result

@router.post("/create", response_model=SpecOrderResponse)
async def create_spec_order(
    spec_order_data: SpecOrderCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новый тип заявки
    
    Требуется право: spec_order_create
    """
    spec_order = await spec_order_service.create_spec_order(
        spec_order_data,
        current_user
    )
    
    return {
        "id": spec_order.id,
        "name": spec_order.name,
        "short_name": spec_order.short_name,
        "code": spec_order.code,
        "is_system": spec_order.is_system,
        "is_default_planned": spec_order.is_default_planned,
        "is_default_primary": spec_order.is_default_primary,
        "description": spec_order.description,
        "orders_count": 0,
        "template_filename": spec_order.template_filename,
    }

@router.put("/{spec_order_id}", response_model=SpecOrderResponse)
async def update_spec_order(
    spec_order_id: int,
    spec_order_data: SpecOrderUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить тип заявки
    
    Требуется право: spec_order_modify
    """
    return await spec_order_service.update_spec_order_with_stats(
        spec_order_id,
        spec_order_data,
        current_user
    )

@router.delete("/{spec_order_id}")
async def delete_spec_order(
    spec_order_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Удалить тип заявки
    
    Требуется право: spec_order_delete
    """
    await spec_order_service.delete_spec_order(
        spec_order_id,
        current_user
    )

    return {
        "status": "success",
        "message": f"Тип заявки с id {spec_order_id} успешно удален"
    }


# ========== ШАБЛОН ДОКУМЕНТА ==========

@router.get("/{spec_order_id}/template/info")
async def get_spec_order_template_info(
    spec_order_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить метаданные привязанного шаблона документа.

    Требуется право: spec_order_read.
    Поля ответа:
      - has_template: bool — привязан ли шаблон в БД
      - template_filename: str | null — оригинальное имя
      - file_exists: bool — лежит ли реально файл на диске сервера
                            (бывает рассинхрон, если файл не успели задеплоить)
    """
    return await spec_order_service.get_spec_order_template_info(
        spec_order_id, current_user
    )


@router.get("/{spec_order_id}/template")
async def download_spec_order_template(
    spec_order_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Скачать привязанный файл шаблона как есть (для правки в Word и заливки обратно).

    Требуется право: spec_order_read.
    Возвращает .docx или .dotx с правильным Content-Type и Content-Disposition
    (включая RFC 6266 для кириллических имён).
    """
    content, filename, media_type = await spec_order_service.download_spec_order_template(
        spec_order_id, current_user
    )
    return Response(
        content=content,
        media_type=media_type,
        headers=build_attachment_headers(filename),
    )


@router.post("/{spec_order_id}/template")
async def upload_spec_order_template(
    spec_order_id: int,
    file: UploadFile = File(..., description="Файл шаблона .docx или .dotx"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Загрузить новый шаблон документа для типа заявки (заменяет старый, если был).

    Требуется право: spec_order_modify.
    Лимит размера: 10 МБ. Допустимые расширения: .docx, .dotx.
    """
    return await spec_order_service.upload_spec_order_template(
        spec_order_id, file, current_user
    )


@router.delete("/{spec_order_id}/template")
async def delete_spec_order_template(
    spec_order_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Снять привязку шаблона и удалить файл с диска.

    Требуется право: spec_order_modify.
    """
    return await spec_order_service.delete_spec_order_template(
        spec_order_id, current_user
    )