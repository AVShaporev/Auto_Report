from typing import Optional, List, Tuple
from pathlib import Path
from fastapi import HTTPException, UploadFile
from model.user import User
from model.spec_journal import Spec_Journal
from data import spec_journal as spec_journal_data
from schema.spec_journal import SpecJournalCreate, SpecJournalUpdate
from schema.pagination import PaginationParams
from database.database import new_session
from config import MEDIA_PATH, MEDIA_TEMPLATES_PATH


# Допустимые расширения загружаемых шаблонов (как у spec_order).
ALLOWED_TEMPLATE_EXTENSIONS = {".docx", ".dotx"}
# Лимит размера файла шаблона: 10 МБ.
MAX_TEMPLATE_SIZE_BYTES = 10 * 1024 * 1024


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def check_permission(
    current_user: User,
    permission: str,
    action: str = "выполнения операции",
) -> None:
    """Проверка наличия права у пользователя"""
    if not hasattr(current_user.role, permission):
        raise HTTPException(
            status_code=500,
            detail=f"Право {permission} не определено в системе",
        )

    has_permission = getattr(current_user.role, permission)
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=f"Недостаточно прав для {action}",
        )


# ========== ПОЛУЧЕНИЕ ==========

async def get_spec_journal_by_id(
    spec_journal_id: int,
    current_user: User,
) -> Spec_Journal:
    """Получить тип журнала по ID с проверкой прав"""
    await check_permission(current_user, "spec_journal_read", "просмотра типов журналов")

    async with new_session() as session:
        spec_journal = await spec_journal_data.get_spec_journal_by_id(session, spec_journal_id)
        if not spec_journal:
            raise HTTPException(
                status_code=404,
                detail=f"Тип журнала с id {spec_journal_id} не найден",
            )
        return spec_journal


async def get_spec_journals_paginated(
    pagination: PaginationParams,
    current_user: User,
    search: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> Tuple[List[Spec_Journal], int]:
    """Получить список типов журналов с пагинацией"""
    await check_permission(current_user, "spec_journal_read", "просмотра списка типов журналов")

    async with new_session() as session:
        items, total = await spec_journal_data.get_spec_journal_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return items, total


async def get_all_spec_journals(current_user: User) -> List[Spec_Journal]:
    """Получить все типы журналов"""
    await check_permission(current_user, "spec_journal_read", "просмотра типов журналов")
    async with new_session() as session:
        return await spec_journal_data.get_spec_journal_all(session)


async def get_spec_journal_options(current_user: User) -> List[Spec_Journal]:
    """Получить минимальную информацию о типах журналов для выпадающих списков"""
    await check_permission(current_user, "spec_journal_read", "просмотра типов журналов")
    async with new_session() as session:
        return await spec_journal_data.get_spec_journal_options(session)


# ========== СОЗДАНИЕ ==========

async def create_spec_journal(
    spec_journal_create: SpecJournalCreate,
    current_user: User,
) -> Spec_Journal:
    """Создать новый тип журнала"""
    await check_permission(current_user, "spec_journal_create", "создания типов журналов")

    async with new_session() as session:
        if await spec_journal_data.check_spec_journal_name_exists(session, spec_journal_create.name):
            raise HTTPException(
                status_code=400,
                detail=f"Тип журнала с названием '{spec_journal_create.name}' уже существует",
            )

        if spec_journal_create.code and await spec_journal_data.check_spec_journal_code_exists(session, spec_journal_create.code):
            raise HTTPException(
                status_code=400,
                detail=f"Тип журнала с кодом '{spec_journal_create.code}' уже существует",
            )

        return await spec_journal_data.create_spec_journal(session, spec_journal_create)


# ========== ОБНОВЛЕНИЕ ==========

async def update_spec_journal(
    spec_journal_id: int,
    spec_journal_update: SpecJournalUpdate,
    current_user: User,
) -> Spec_Journal:
    """Обновить тип журнала"""
    await check_permission(current_user, "spec_journal_modify", "изменения типов журналов")

    async with new_session() as session:
        existing = await spec_journal_data.get_spec_journal_by_id(session, spec_journal_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип журнала с id {spec_journal_id} не найден",
            )

        if spec_journal_update.name and spec_journal_update.name != existing.name:
            if await spec_journal_data.check_spec_journal_name_exists(session, spec_journal_update.name, spec_journal_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип журнала с названием '{spec_journal_update.name}' уже существует",
                )

        if spec_journal_update.code and spec_journal_update.code != existing.code:
            if await spec_journal_data.check_spec_journal_code_exists(session, spec_journal_update.code, spec_journal_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип журнала с кодом '{spec_journal_update.code}' уже существует",
                )

        return await spec_journal_data.update_spec_journal(session, spec_journal_id, spec_journal_update)


# ========== УДАЛЕНИЕ ==========

async def delete_spec_journal(
    spec_journal_id: int,
    current_user: User,
) -> bool:
    """Удалить тип журнала"""
    await check_permission(current_user, "spec_journal_delete", "удаления типов журналов")

    async with new_session() as session:
        spec_journal = await spec_journal_data.get_spec_journal_by_id(session, spec_journal_id)
        if not spec_journal:
            raise HTTPException(
                status_code=404,
                detail=f"Тип журнала с id {spec_journal_id} не найден",
            )

        if spec_journal.is_system:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить системную запись '{spec_journal.name}' — она необходима для работы системы.",
            )

        # Снимаем файл с диска, если был привязан.
        if spec_journal.template_storage_path:
            abs_path = MEDIA_PATH / spec_journal.template_storage_path
            if abs_path.exists():
                abs_path.unlink()

        return await spec_journal_data.delete_spec_journal(session, spec_journal_id)


# ========== ШАБЛОН ДОКУМЕНТА ==========

async def upload_spec_journal_template(
    spec_journal_id: int,
    upload: UploadFile,
    current_user: User,
) -> dict:
    """Загрузить .docx/.dotx-шаблон для типа журнала."""
    await check_permission(current_user, "spec_journal_modify", "загрузки шаблона документа")

    if not upload.filename:
        raise HTTPException(status_code=400, detail="Не указано имя файла")

    ext = Path(upload.filename).suffix.lower()
    if ext not in ALLOWED_TEMPLATE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Допустимые форматы шаблона: {', '.join(sorted(ALLOWED_TEMPLATE_EXTENSIONS))}. Загружено: {ext or '<без расширения>'}",
        )

    contents = await upload.read()
    if len(contents) > MAX_TEMPLATE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой ({len(contents)} байт). Лимит: {MAX_TEMPLATE_SIZE_BYTES} байт.",
        )

    async with new_session() as session:
        existing = await spec_journal_data.get_spec_journal_by_id(session, spec_journal_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип журнала с id {spec_journal_id} не найден",
            )

        # Имя файла в storage: journal_{id}{ext}. Префикс journal_ — чтобы
        # пространство имён не пересекалось с шаблонами spec_orders.
        storage_filename = f"journal_{spec_journal_id}{ext}"
        storage_path_rel = f"templates/{storage_filename}"
        storage_path_abs = MEDIA_TEMPLATES_PATH / storage_filename

        # Удаляем старый файл, если был другой расширением.
        if existing.template_storage_path and existing.template_storage_path != storage_path_rel:
            old_abs = MEDIA_PATH / existing.template_storage_path
            if old_abs.exists():
                old_abs.unlink()

        storage_path_abs.write_bytes(contents)

        spec_journal = await spec_journal_data.set_spec_journal_template(
            session,
            spec_journal_id,
            template_filename=upload.filename,
            template_storage_path=storage_path_rel,
        )

        return {
            "id": spec_journal.id,
            "template_filename": spec_journal.template_filename,
            "size_bytes": len(contents),
        }


async def delete_spec_journal_template(
    spec_journal_id: int,
    current_user: User,
) -> dict:
    """Удалить привязку шаблона и сам файл с диска."""
    await check_permission(current_user, "spec_journal_modify", "удаления шаблона документа")

    async with new_session() as session:
        existing = await spec_journal_data.get_spec_journal_by_id(session, spec_journal_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Тип журнала с id {spec_journal_id} не найден",
            )

        if not existing.template_storage_path:
            raise HTTPException(
                status_code=404,
                detail=f"У типа журнала '{existing.name}' нет привязанного шаблона",
            )

        abs_path = MEDIA_PATH / existing.template_storage_path
        await spec_journal_data.clear_spec_journal_template(session, spec_journal_id)

        if abs_path.exists():
            abs_path.unlink()

        return {"status": "ok", "id": spec_journal_id}


async def get_spec_journal_template_info(
    spec_journal_id: int,
    current_user: User,
) -> dict:
    """Метаданные привязанного шаблона + признак наличия файла на диске."""
    await check_permission(current_user, "spec_journal_read", "просмотра шаблона документа")

    async with new_session() as session:
        spec_journal = await spec_journal_data.get_spec_journal_by_id(session, spec_journal_id)
        if not spec_journal:
            raise HTTPException(
                status_code=404,
                detail=f"Тип журнала с id {spec_journal_id} не найден",
            )

        if not spec_journal.template_storage_path:
            return {
                "id": spec_journal.id,
                "has_template": False,
                "template_filename": None,
                "file_exists": False,
            }

        abs_path = MEDIA_PATH / spec_journal.template_storage_path
        return {
            "id": spec_journal.id,
            "has_template": True,
            "template_filename": spec_journal.template_filename,
            "file_exists": abs_path.exists(),
        }


async def download_spec_journal_template(
    spec_journal_id: int,
    current_user: User,
):
    """Прочитать содержимое привязанного шаблона + оригинальное имя.

    Returns: (content_bytes, original_filename, media_type).
    """
    await check_permission(current_user, "spec_journal_read", "скачивания шаблона документа")

    async with new_session() as session:
        spec_journal = await spec_journal_data.get_spec_journal_by_id(session, spec_journal_id)
        if not spec_journal:
            raise HTTPException(
                status_code=404,
                detail=f"Тип журнала с id {spec_journal_id} не найден",
            )

        if not spec_journal.template_storage_path:
            raise HTTPException(
                status_code=404,
                detail=f"Для вида журнала «{spec_journal.name}» шаблон не загружен.",
            )

        abs_path = MEDIA_PATH / spec_journal.template_storage_path
        if not abs_path.exists():
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Файл шаблона отсутствует на диске сервера "
                    f"({spec_journal.template_storage_path}). Загрузите шаблон заново."
                ),
            )

        suffix = abs_path.suffix.lower()
        if suffix == ".dotx":
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.template"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        return abs_path.read_bytes(), spec_journal.template_filename, media_type
