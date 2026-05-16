from typing import Optional, Tuple
from pathlib import Path

from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from weasyprint import HTML

from database.database import new_session
from model.user import User
from model.object import Object as ObjectModel
from model.contract import Contract
from model.organization import Organization
from model.locality import Locality
from model.street import Street
from service.object import check_permission


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "blanks"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=False,
    lstrip_blocks=False,
)


def _build_address(obj: ObjectModel) -> str:
    parts = []
    if obj.region and obj.region.name:
        spec = getattr(obj.region, "spec_region", None)
        suffix = f" {spec.name}" if spec and spec.name else ""
        parts.append(f"{obj.region.name}{suffix}".strip())
    if obj.arial and obj.arial.name:
        spec = getattr(obj.arial, "spec_arial", None)
        suffix = f" {spec.name}" if spec and spec.name else ""
        parts.append(f"{obj.arial.name}{suffix}".strip())
    if obj.locality and obj.locality.name:
        sl = getattr(obj.locality, "spec_locality", None)
        prefix = f"{sl.short_name} " if sl and getattr(sl, "short_name", None) else ""
        parts.append(f"{prefix}{obj.locality.name}".strip())
    if obj.street and obj.street.name:
        ss = getattr(obj.street, "spec_street", None)
        prefix = f"{ss.short_name} " if ss and getattr(ss, "short_name", None) else ""
        parts.append(f"{prefix}{obj.street.name}".strip())
    if obj.build_number:
        prefix = obj.spec_build.name if obj.spec_build and obj.spec_build.name else "д."
        parts.append(f"{prefix} {obj.build_number}".strip())
    if obj.room_number:
        prefix = obj.spec_room.name if obj.spec_room and obj.spec_room.name else "пом."
        parts.append(f"{prefix} {obj.room_number}".strip())
    return ", ".join(parts) if parts else "—"


def _build_org_address(org: Optional[Organization]) -> str:
    """Адрес юрлица: индекс + регион + район + населённый пункт + улица + дом + помещение."""
    if not org:
        return ""
    parts = []
    if getattr(org, "postal_code", None):
        parts.append(str(org.postal_code))
    if getattr(org, "region", None) and getattr(org.region, "name", None):
        parts.append(org.region.name)
    if getattr(org, "arial", None) and getattr(org.arial, "name", None):
        parts.append(org.arial.name)
    if getattr(org, "locality", None) and getattr(org.locality, "name", None):
        sl = getattr(org.locality, "spec_locality", None)
        prefix = f"{sl.short_name} " if sl and getattr(sl, "short_name", None) else ""
        parts.append(f"{prefix}{org.locality.name}".strip())
    if getattr(org, "street", None) and getattr(org.street, "name", None):
        ss = getattr(org.street, "spec_street", None)
        prefix = f"{ss.short_name} " if ss and getattr(ss, "short_name", None) else ""
        parts.append(f"{prefix}{org.street.name}".strip())
    if getattr(org, "build_number", None):
        parts.append(f"д. {org.build_number}")
    if getattr(org, "room_number", None):
        parts.append(f"пом. {org.room_number}")
    return ", ".join(p for p in parts if p)


async def _load_object_with_relations(session, object_id: int) -> ObjectModel:
    # Подгружаем заказчика контракта вместе с его адресом и исполнителя контракта
    # тоже с адресом (понадобится для блока «Договор на ТО» в журнале).
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
            selectinload(ObjectModel.contract).selectinload(Contract.customer),
            selectinload(ObjectModel.contract)
                .selectinload(Contract.executor)
                .selectinload(Organization.locality)
                .selectinload(Locality.spec_locality),
            selectinload(ObjectModel.contract)
                .selectinload(Contract.executor)
                .selectinload(Organization.street)
                .selectinload(Street.spec_street),
            selectinload(ObjectModel.contract)
                .selectinload(Contract.executor)
                .selectinload(Organization.region),
            selectinload(ObjectModel.contract)
                .selectinload(Contract.executor)
                .selectinload(Organization.arial),
        )
    )
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Объект с id {object_id} не найден")
    return obj


def _organization_name(org: Optional[Organization]) -> str:
    if not org:
        return ""
    return (org.name or "").strip()


def _format_contract_date(contract: Optional[Contract]) -> str:
    if not contract or not contract.date_of_consclusion:
        return ""
    d = contract.date_of_consclusion
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


async def render_object_fire_protection_log_pdf(
    object_id: int,
    current_user: User,
    blank_rows: int = 25,
) -> Tuple[bytes, str]:
    """
    Сформировать PDF бланка журнала эксплуатации систем противопожарной защиты
    для объекта. Бланк пустой, заполняется ответственным на объекте.
    """
    await check_permission(
        current_user, "object_read", "формирования бланка журнала ПЗ"
    )

    async with new_session() as session:
        obj = await _load_object_with_relations(session, object_id)

        contract = obj.contract
        customer = contract.customer if contract else None
        executor = contract.executor if contract else None

        ctx = {
            "object": {
                "id": obj.id,
                "name": obj.name or "",
            },
            "object_address": _build_address(obj),
            "customer": {
                "name": _organization_name(customer),
                "short_name": (getattr(customer, "short_name", "") or "").strip(),
            },
            "executor": {
                "name": _organization_name(executor),
                "short_name": (getattr(executor, "short_name", "") or "").strip(),
                "address": _build_org_address(executor),
                "telephone": (getattr(executor, "telephone", "") or "").strip(),
            },
            "contract": {
                "number": (contract.number if contract else "") or "",
                "date": _format_contract_date(contract),
            },
            "responsible_face": obj.responsible_face or "",
            "responsible_contact": obj.responsible_faces_contact or "",
            "blank_rows": blank_rows,
        }

    template = _jinja_env.get_template("fire_protection_log.html")
    html_str = template.render(**ctx)

    pdf_bytes = HTML(string=html_str, base_url=str(TEMPLATES_DIR)).write_pdf()
    filename = f"fire_protection_log_{object_id}.pdf"
    return pdf_bytes, filename
