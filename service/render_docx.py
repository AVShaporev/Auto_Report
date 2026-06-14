"""
Рендер заполненного документа (.docx / .pdf) для заявки на базе .docx-/.dotx-шаблона,
привязанного к её типу (`spec_order.template_storage_path`).

Параллельная альтернатива HTML+weasyprint-пайплайну из service/order_pdf.py:
здесь jinja-разметка живёт прямо внутри Word-документа (docxtpl), что даёт
не-разработчикам возможность редактировать шаблон в MS Word.

PDF-вариант требует установленного LibreOffice headless на сервере
(пакет `libreoffice-core` / `libreoffice-writer`). Если LibreOffice не
найден, запрос format=pdf возвращает 503 с понятным сообщением.
"""
from __future__ import annotations

import asyncio
import io
import os
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote

from fastapi import HTTPException
from docxtpl import DocxTemplate
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.database import new_session
from model.user import User
from model.order import Order
from model.contract import Contract
from model.object import Object as ObjectModel
from model.organization import Organization
from model.locality import Locality
from model.street import Street
from model.spec_journal import Spec_Journal
from model.objects_equipment import Objects_Equipment
from config import MEDIA_PATH
from service.order import check_permission
from service.order_pdf import (
    _RUSSIAN_MONTHS_GEN,
    _format_director_full_name,
    _build_address,
    _build_equipment_groups,
)


# python-docx (на котором сидит docxtpl) проверяет content_type главного
# документа в zip-пакете: ждёт `.../wordprocessingml.document.main+xml`.
# Файлы `.dotx` приходят с `.../wordprocessingml.template.main+xml` и
# отбиваются ValueError'ом «file ... is not a Word file».
# Решение: перепаковать .dotx в bytes с заменой content_type на document.
_TEMPLATE_CT = b"application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
_DOCUMENT_CT = b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def _open_docx_template(path: Path) -> DocxTemplate:
    """Загрузить .docx или .dotx как DocxTemplate. Для .dotx — перепаковать
    в памяти с content_type документа, чтобы python-docx его принял.
    Сам XML документа не меняется, jinja-разметка сохраняется как есть."""
    if path.suffix.lower() != ".dotx":
        return DocxTemplate(str(path))

    buf = io.BytesIO()
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(
        buf, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(_TEMPLATE_CT, _DOCUMENT_CT)
            zout.writestr(item, data)
    buf.seek(0)
    return DocxTemplate(buf)


# ========== ХЕЛПЕРЫ ДЛЯ КОНТЕКСТА ==========

def _today_short() -> str:
    """07.06.2026"""
    return date.today().strftime("%d.%m.%Y")


def _today_long() -> str:
    """«07» июня 2026 г."""
    d = date.today()
    return f"«{d.day:02d}» {_RUSSIAN_MONTHS_GEN[d.month - 1]} {d.year} г."


def _fmt_date(d: Optional[date]) -> str:
    return d.strftime("%d.%m.%Y") if d else ""


def _build_org_address(org: Optional[Organization]) -> str:
    """
    Собрать полный адрес организации одной строкой.
    Аналог _build_address из order_pdf.py, но для Organization
    (у которой набор полей и связей идентичен Object).
    """
    if not org:
        return ""
    parts: list[str] = []
    if org.postal_code:
        parts.append(org.postal_code)
    if org.region and org.region.name:
        sr = getattr(org.region, "spec_region", None)
        suffix = f" {sr.name}" if sr and sr.name else ""
        parts.append(f"{org.region.name}{suffix}")
    if org.arial and org.arial.name:
        sa = getattr(org.arial, "spec_arial", None)
        suffix = f" {sa.name}" if sa and sa.name else ""
        parts.append(f"{org.arial.name}{suffix}")
    if org.locality and org.locality.name:
        sl = getattr(org.locality, "spec_locality", None)
        prefix = f"{sl.short_name} " if sl and getattr(sl, "short_name", None) else ""
        parts.append(f"{prefix}{org.locality.name}".strip())
    if org.street and org.street.name:
        ss = getattr(org.street, "spec_street", None)
        prefix = f"{ss.short_name} " if ss and getattr(ss, "short_name", None) else ""
        parts.append(f"{prefix}{org.street.name}".strip())
    if org.build_number:
        sb = getattr(org, "spec_build", None)
        prefix = sb.name if sb and sb.name else "д."
        parts.append(f"{prefix} {org.build_number}".strip())
    if org.room_number:
        parts.append(f"пом. {org.room_number}".strip())
    return ", ".join(p for p in parts if p)


def _org_to_dict(org: Optional[Organization]) -> dict:
    """Структура для шаблона: {{ customer.name }}, {{ customer.director_full_name }}, …"""
    if not org:
        return {
            "name": "",
            "short_name": "",
            "inn": "",
            "kpp": "",
            "director_full_name": "",
            "address": "",
        }
    return {
        "name": org.name or "",
        "short_name": org.short_name or "",
        "inn": org.inn or "",
        "kpp": org.kpp or "",
        "director_full_name": _format_director_full_name(org),
        "address": _build_org_address(org),
    }


def _build_context(order: Order) -> dict:
    """Собрать словарь для docxtpl. Список ключей задокументирован в Phase 3."""
    contract: Optional[Contract] = order.contract
    customer = contract.customer if contract else None
    executor = contract.executor if contract else None
    obj = order.object
    user = order.user

    return {
        "order": {
            "number": order.number or "",
            "created_at": _fmt_date(order.created_at),
            "description": order.description or "",
        },
        "contract": {
            "number": contract.number if contract else "",
            "date_of_consclusion": _fmt_date(contract.date_of_consclusion if contract else None),
            "date_of_completion": _fmt_date(contract.date_of_completion if contract else None),
            "subject": (contract.subject or "") if contract else "",
            "short_subject": (contract.short_subject or "") if contract else "",
        },
        "customer": _org_to_dict(customer),
        "executor": _org_to_dict(executor),
        "object": {
            "name": (obj.name or "") if obj else "",
            "address": _build_address(obj) if obj else "",
            "responsible_face": (obj.responsible_face or "") if obj else "",
            "responsible_faces_contact": (obj.responsible_faces_contact or "") if obj else "",
        },
        "user": {
            "full_name": (user.full_name or "") if user else "",
            "role_name": (user.role.name or "") if (user and user.role) else "",
        },
        "today": _today_short(),
        "today_long": _today_long(),
        # Сгруппированное по системам оборудование объекта — для таблицы в акте.
        # Структура: [{"index": 1, "system_name": "...", "rows": [{"index": "1.1", "name": "...", "count": N}, ...]}, ...]
        # В docxtpl-шаблоне: {%tr for group in equipment_groups %} в одной строке,
        # {%tr for row in group.rows %} во вложенной строке той же таблицы.
        "equipment_groups": _build_equipment_groups(obj) if obj else [],
    }


# ========== ЗАГРУЗКА ORDER СО ВСЕМИ СВЯЗЯМИ ==========
# Отдельная от order_pdf._load_order_with_relations, потому что докручиваем
# географию для customer/executor и role для user (HTML-пайплайн их не грузит).

async def _load_order_for_docx(session, order_id: int) -> Order:
    customer_load = (
        selectinload(Order.contract)
        .selectinload(Contract.customer)
    )
    executor_load = (
        selectinload(Order.contract)
        .selectinload(Contract.executor)
    )

    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.spec_order),
            selectinload(Order.user).selectinload(User.role),
            # customer + его география
            customer_load.selectinload(Organization.region),
            customer_load.selectinload(Organization.arial),
            customer_load.selectinload(Organization.locality).selectinload(Locality.spec_locality),
            customer_load.selectinload(Organization.street).selectinload(Street.spec_street),
            customer_load.selectinload(Organization.spec_build),
            # executor + его география
            executor_load.selectinload(Organization.region),
            executor_load.selectinload(Organization.arial),
            executor_load.selectinload(Organization.locality).selectinload(Locality.spec_locality),
            executor_load.selectinload(Organization.street).selectinload(Street.spec_street),
            executor_load.selectinload(Organization.spec_build),
            # object + его география
            selectinload(Order.object).selectinload(ObjectModel.region),
            selectinload(Order.object).selectinload(ObjectModel.arial),
            selectinload(Order.object).selectinload(ObjectModel.locality).selectinload(Locality.spec_locality),
            selectinload(Order.object).selectinload(ObjectModel.street).selectinload(Street.spec_street),
            selectinload(Order.object).selectinload(ObjectModel.spec_build),
            selectinload(Order.object).selectinload(ObjectModel.spec_room),
            # objects_equipments + equipment + spec_system — для equipment_groups в шаблоне
            selectinload(Order.object)
                .selectinload(ObjectModel.objects_equipments)
                .selectinload(Objects_Equipment.equipment),
            selectinload(Order.object)
                .selectinload(ObjectModel.objects_equipments)
                .selectinload(Objects_Equipment.spec_system),
        )
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail=f"Заявка с id {order_id} не найдена")
    return order


# ========== ОСНОВНОЙ РЕНДЕР ==========

ALLOWED_RENDER_FORMATS = {"docx", "pdf"}


async def render_order_document(
    order_id: int,
    fmt: str,
    current_user: User,
) -> Tuple[bytes, str, str]:
    """
    Сформировать заполненный документ по заявке.

    Returns: (content_bytes, filename, media_type).
    """
    if fmt not in ALLOWED_RENDER_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат: {fmt!r}. Доступны: {sorted(ALLOWED_RENDER_FORMATS)}.",
        )

    await check_permission(current_user, "order_read", f"скачивания {fmt.upper()}-акта")

    async with new_session() as session:
        order = await _load_order_for_docx(session, order_id)

        spec_order = order.spec_order
        if not spec_order:
            raise HTTPException(status_code=400, detail="У заявки не указан тип")
        if not spec_order.template_storage_path:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Для типа заявки «{spec_order.name}» не загружен шаблон документа. "
                    "Загрузите .docx/.dotx через справочник «Типы заявок»."
                ),
            )

        template_abs = MEDIA_PATH / spec_order.template_storage_path
        if not template_abs.exists():
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Файл шаблона отсутствует на диске сервера "
                    f"({spec_order.template_storage_path}). Свяжитесь с администратором."
                ),
            )

        context = _build_context(order)

    suggested_stem = f"act_order_{order.number or order.id}_{spec_order.code or 'doc'}"
    # Чистим символы, которые ОС не любит в именах файлов.
    suggested_stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in suggested_stem)

    # Рендер в .docx через docxtpl.
    doc = _open_docx_template(template_abs)
    doc.render(context)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        docx_path = tmp_dir / f"{suggested_stem}.docx"
        doc.save(str(docx_path))

        if fmt == "docx":
            return (
                docx_path.read_bytes(),
                docx_path.name,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        # fmt == "pdf"
        pdf_path = await _convert_to_pdf(docx_path, tmp_dir)
        return pdf_path.read_bytes(), pdf_path.name, "application/pdf"


async def render_orders_bulk_zip(
    order_ids: list[int],
    fmt: str,
    current_user: User,
) -> Tuple[bytes, str, str]:
    """
    Сформировать ZIP-архив с актами по нескольким заявкам.

    Каждая заявка рендерится через render_order_document (своим шаблоном
    по spec_order.template_storage_path). Ошибки на отдельных заявках
    НЕ блокируют остальные — в архив добавляется errors.txt со списком.

    Limit: 100 заявок за запрос. PDF-режим заметно медленнее (soffice на
    каждую заявку), не рекомендуется для крупных пакетов.

    Returns: (zip_bytes, filename, "application/zip").
    """
    if fmt not in ALLOWED_RENDER_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат: {fmt!r}. Доступны: {sorted(ALLOWED_RENDER_FORMATS)}.",
        )
    if not order_ids:
        raise HTTPException(status_code=400, detail="Не указаны id заявок")
    if len(order_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Слишком много заявок за раз ({len(order_ids)}). Максимум — 100.",
        )

    # check_permission делается внутри render_order_document на каждую заявку,
    # отдельно дублировать не нужно.

    successes: list[Tuple[str, bytes]] = []
    errors: list[Tuple[int, str]] = []

    for order_id in order_ids:
        try:
            content, filename, _media = await render_order_document(
                order_id, fmt, current_user
            )
            successes.append((filename, content))
        except HTTPException as e:
            errors.append((order_id, f"HTTP {e.status_code}: {e.detail}"))
        except Exception as e:  # noqa: BLE001 — намеренно ловим всё, чтобы один битый файл не валил пакет
            errors.append((order_id, f"{type(e).__name__}: {e}"))

    # Если все провалились — общий 400 с первой причиной (юзер увидит понятный
    # текст, а не пустой zip).
    if not successes:
        first_err = errors[0][1] if errors else "неизвестная ошибка"
        raise HTTPException(
            status_code=400,
            detail=f"Ни один из {len(order_ids)} актов не удалось сформировать. "
                   f"Первая ошибка: {first_err}",
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Коллизии имён (две заявки с одинаковым номером и типом) разрешаем
        # суффиксом _2, _3, … — чтобы файлы внутри ZIP не перезаписали друг друга.
        used_counts: dict[str, int] = {}
        for filename, content in successes:
            base, ext = os.path.splitext(filename)
            n = used_counts.get(filename, 0)
            final_name = filename if n == 0 else f"{base}_{n + 1}{ext}"
            used_counts[filename] = n + 1
            zf.writestr(final_name, content)

        if errors:
            lines = [f"order_id={oid}: {msg}" for oid, msg in errors]
            zf.writestr(
                "errors.txt",
                f"Не удалось сформировать {len(errors)} из {len(order_ids)} актов:\n\n"
                + "\n".join(lines),
            )

    archive_name = f"acts_{date.today().strftime('%Y-%m-%d')}_{fmt}.zip"
    return buf.getvalue(), archive_name, "application/zip"


def build_attachment_headers(filename: str) -> dict:
    """
    Заголовки HTTP для скачивания файла с поддержкой не-ASCII имени (RFC 6266).

    `filename="..."` — ASCII-fallback для старых клиентов (символы, которые
    не помещаются в latin-1, заменяются на '_').
    `filename*=UTF-8''...` — корректное UTF-8-имя для современных браузеров.

    Решает UnicodeEncodeError 'latin-1' codec can't encode characters,
    который возникает, если в имя файла попадает кириллица.
    """
    ascii_fallback = "".join(ch if ord(ch) < 128 else "_" for ch in filename) or "document"
    quoted = quote(filename, safe="")
    return {
        "Content-Disposition": (
            f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quoted}'
        ),
    }


async def _convert_to_pdf(docx_path: Path, work_dir: Path) -> Path:
    """
    Запускает LibreOffice headless: .docx -> .pdf в той же work_dir.

    Профиль soffice (UserInstallation) и HOME принудительно перенаправлены
    в work_dir: на продакшене HOME юзера autoreport read-only (systemd
    ProtectHome=yes), без override soffice падает с
    `dconf-CRITICAL: unable to create file '~/.cache/dconf/user': Read-only file system`.
    """
    profile_dir = work_dir / "lo_profile"
    profile_dir.mkdir(exist_ok=True)
    # UserInstallation должен быть file://-URI на абсолютный путь.
    user_install = f"file://{profile_dir.resolve().as_posix()}"

    env = {
        **os.environ,
        "HOME": str(work_dir),
        "XDG_CACHE_HOME": str(work_dir / "cache"),
        "XDG_CONFIG_HOME": str(work_dir / "config"),
        "XDG_DATA_HOME": str(work_dir / "data"),
    }

    try:
        proc = await asyncio.create_subprocess_exec(
            "soffice",
            f"-env:UserInstallation={user_install}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(work_dir),
            str(docx_path),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail=(
                "LibreOffice (soffice) не установлен на сервере. "
                "Скачайте .docx и сконвертируйте на своей машине, "
                "либо попросите администратора установить пакет libreoffice."
            ),
        )

    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=(
                "LibreOffice не смог сконвертировать .docx -> .pdf. "
                f"stdout: {stdout.decode(errors='replace')[:200]}; "
                f"stderr: {stderr.decode(errors='replace')[:200]}"
            ),
        )

    pdf_path = work_dir / f"{docx_path.stem}.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"LibreOffice не создал PDF-файл по ожидаемому пути {pdf_path.name}",
        )
    return pdf_path


# ========== РЕНДЕР ЖУРНАЛА ОБЪЕКТА ==========
# Журнал — бланк, привязанный к ОБЪЕКТУ (а не к заявке). Тип журнала
# выбирается из справочника spec_journals; шаблон лежит у типа.

async def _load_object_for_journal(session, object_id: int) -> ObjectModel:
    """Загрузить объект со всеми связями, нужными для шапки журнала."""
    stmt = (
        select(ObjectModel)
        .where(ObjectModel.id == object_id)
        .options(
            selectinload(ObjectModel.region),
            selectinload(ObjectModel.arial),
            selectinload(ObjectModel.locality).selectinload(Locality.spec_locality),
            selectinload(ObjectModel.street).selectinload(Street.spec_street),
            selectinload(ObjectModel.spec_build),
            selectinload(ObjectModel.spec_room),
            # contract + customer + executor с их географией
            selectinload(ObjectModel.contract).selectinload(Contract.customer).selectinload(Organization.region),
            selectinload(ObjectModel.contract).selectinload(Contract.customer).selectinload(Organization.arial),
            selectinload(ObjectModel.contract).selectinload(Contract.customer).selectinload(Organization.locality).selectinload(Locality.spec_locality),
            selectinload(ObjectModel.contract).selectinload(Contract.customer).selectinload(Organization.street).selectinload(Street.spec_street),
            selectinload(ObjectModel.contract).selectinload(Contract.customer).selectinload(Organization.spec_build),
            selectinload(ObjectModel.contract).selectinload(Contract.executor).selectinload(Organization.region),
            selectinload(ObjectModel.contract).selectinload(Contract.executor).selectinload(Organization.arial),
            selectinload(ObjectModel.contract).selectinload(Contract.executor).selectinload(Organization.locality).selectinload(Locality.spec_locality),
            selectinload(ObjectModel.contract).selectinload(Contract.executor).selectinload(Organization.street).selectinload(Street.spec_street),
            selectinload(ObjectModel.contract).selectinload(Contract.executor).selectinload(Organization.spec_build),
        )
    )
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()

    if not obj:
        raise HTTPException(status_code=404, detail=f"Объект с id {object_id} не найден")
    return obj


def _build_journal_context(obj: ObjectModel) -> dict:
    """Собрать словарь для docxtpl-шаблона журнала. Список ключей идёт в DocsView (Phase 3)."""
    contract: Optional[Contract] = obj.contract
    customer = contract.customer if contract else None
    executor = contract.executor if contract else None

    return {
        "object": {
            "name": obj.name or "",
            "address": _build_address(obj),
            "responsible_face": obj.responsible_face or "",
            "responsible_faces_contact": obj.responsible_faces_contact or "",
        },
        "contract": {
            "number": contract.number if contract else "",
            "date_of_consclusion": _fmt_date(contract.date_of_consclusion if contract else None),
            "date_of_completion": _fmt_date(contract.date_of_completion if contract else None),
            "subject": (contract.subject or "") if contract else "",
            "short_subject": (contract.short_subject or "") if contract else "",
        },
        "customer": _org_to_dict(customer),
        "executor": _org_to_dict(executor),
        "today": _today_short(),
        "today_long": _today_long(),
    }


async def render_object_journal_document(
    object_id: int,
    journal_type_id: int,
    fmt: str,
    current_user: User,
) -> Tuple[bytes, str, str]:
    """
    Сформировать заполненный бланк журнала для объекта по выбранному типу журнала.

    Returns: (content_bytes, filename, media_type).
    """
    if fmt not in ALLOWED_RENDER_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат: {fmt!r}. Доступны: {sorted(ALLOWED_RENDER_FORMATS)}.",
        )

    await check_permission(current_user, "object_read", f"скачивания {fmt.upper()}-журнала")

    async with new_session() as session:
        obj = await _load_object_for_journal(session, object_id)

        spec_journal = await session.get(Spec_Journal, journal_type_id)
        if not spec_journal:
            raise HTTPException(
                status_code=404,
                detail=f"Тип журнала с id {journal_type_id} не найден",
            )
        if not spec_journal.template_storage_path:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Для типа журнала «{spec_journal.name}» не загружен шаблон документа. "
                    "Загрузите .docx/.dotx через справочник «Виды журналов»."
                ),
            )

        template_abs = MEDIA_PATH / spec_journal.template_storage_path
        if not template_abs.exists():
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Файл шаблона отсутствует на диске сервера "
                    f"({spec_journal.template_storage_path}). Свяжитесь с администратором."
                ),
            )

        context = _build_journal_context(obj)

    suggested_stem = f"journal_{spec_journal.code or spec_journal.id}_object_{obj.id}_{obj.name or ''}"
    suggested_stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in suggested_stem)

    doc = _open_docx_template(template_abs)
    doc.render(context)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        docx_path = tmp_dir / f"{suggested_stem}.docx"
        doc.save(str(docx_path))

        if fmt == "docx":
            return (
                docx_path.read_bytes(),
                docx_path.name,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        pdf_path = await _convert_to_pdf(docx_path, tmp_dir)
        return pdf_path.read_bytes(), pdf_path.name, "application/pdf"


async def render_object_journals_bulk_zip(
    object_ids: list[int],
    journal_type_id: int,
    fmt: str,
    current_user: User,
) -> Tuple[bytes, str, str]:
    """ZIP с журналами по одному виду spec_journal для пакета объектов.

    Логика повторяет render_orders_bulk_zip: ошибка на одном объекте не
    блокирует остальные, errors.txt прикладывается в архив. Лимит — 100.
    """
    if fmt not in ALLOWED_RENDER_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат: {fmt!r}. Доступны: {sorted(ALLOWED_RENDER_FORMATS)}.",
        )
    if not object_ids:
        raise HTTPException(status_code=400, detail="Не указаны id объектов")
    if len(object_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Слишком много объектов за раз ({len(object_ids)}). Максимум — 100.",
        )

    successes: list[Tuple[str, bytes]] = []
    errors: list[Tuple[int, str]] = []

    for object_id in object_ids:
        try:
            content, filename, _media = await render_object_journal_document(
                object_id, journal_type_id, fmt, current_user
            )
            successes.append((filename, content))
        except HTTPException as e:
            errors.append((object_id, f"HTTP {e.status_code}: {e.detail}"))
        except Exception as e:  # noqa: BLE001
            errors.append((object_id, f"{type(e).__name__}: {e}"))

    if not successes:
        first_err = errors[0][1] if errors else "неизвестная ошибка"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Ни один из {len(object_ids)} журналов не удалось сформировать. "
                f"Первая ошибка: {first_err}"
            ),
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        used_counts: dict[str, int] = {}
        for filename, content in successes:
            base, ext = os.path.splitext(filename)
            n = used_counts.get(filename, 0)
            final_name = filename if n == 0 else f"{base}_{n + 1}{ext}"
            used_counts[filename] = n + 1
            zf.writestr(final_name, content)

        if errors:
            lines = [f"object_id={oid}: {msg}" for oid, msg in errors]
            zf.writestr(
                "errors.txt",
                f"Не удалось сформировать {len(errors)} из {len(object_ids)} журналов:\n\n"
                + "\n".join(lines),
            )

    archive_name = f"journals_{date.today().strftime('%Y-%m-%d')}_{fmt}.zip"
    return buf.getvalue(), archive_name, "application/zip"
