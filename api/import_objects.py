"""Импорт объектов и оборудования из Excel. Логика — service/import_objects.py."""
from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from core.dependencies import get_current_active_user
from model.user import User
from service import import_objects as import_service
from service.object import check_permission
from service.render_docx import build_attachment_headers

router = APIRouter(prefix="/api/import/objects", tags=["import"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/template")
async def download_template(current_user: User = Depends(get_current_active_user)):
    """Шаблон .xlsx с выпадающими списками из справочников организации."""
    await check_permission(current_user, "object_create", "импорта объектов")
    content = await import_service.build_template()
    return Response(content=content, media_type=XLSX,
                    headers=build_attachment_headers("Импорт объектов и оборудования.xlsx"))


@router.post("/preview")
async def preview_import(
    contract_id: int = Form(..., ge=1),
    file: UploadFile = File(..., description="Заполненный шаблон .xlsx"),
    current_user: User = Depends(get_current_active_user),
):
    """Разбор файла без записи: что будет создано и ошибки по строкам."""
    await check_permission(current_user, "object_create", "импорта объектов")
    plan = await import_service.build_plan(await file.read(), contract_id)
    return plan.to_dict()


@router.post("/commit")
async def commit_import(
    contract_id: int = Form(..., ge=1),
    file: UploadFile = File(..., description="Заполненный шаблон .xlsx"),
    current_user: User = Depends(get_current_active_user),
):
    """Импорт. Если в файле ошибки — 400 с предпросмотром, ничего не записывается."""
    return await import_service.commit_plan(await file.read(), contract_id, current_user)
