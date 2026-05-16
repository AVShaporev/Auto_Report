from typing import Optional, Tuple
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from weasyprint import HTML

from database.database import new_session
from model.user import User
from model.order import Order
from model.contract import Contract
from model.object import Object as ObjectModel
from model.organization import Organization
from model.locality import Locality
from model.street import Street
from model.objects_equipment import Objects_Equipment
from service.order import check_permission


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "blanks"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=False,
    lstrip_blocks=False,
)

_RUSSIAN_MONTHS_PREP = [
    "январе", "феврале", "марте", "апреле", "мае", "июне",
    "июле", "августе", "сентябре", "октябре", "ноябре", "декабре",
]
_RUSSIAN_MONTHS_GEN = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def _format_work_period(d: date) -> str:
    return f"{_RUSSIAN_MONTHS_PREP[d.month - 1]} {d.year} года"


def _format_full_date(d: date) -> str:
    return f"{d.day} {_RUSSIAN_MONTHS_GEN[d.month - 1]} {d.year} г."


def _format_director_full_name(org: Organization) -> str:
    parts = [
        (getattr(org, "drector_last_name", "") or "").strip(),
        (getattr(org, "director_first_name", "") or "").strip(),
        (getattr(org, "drector_surname", "") or "").strip(),
    ]
    return " ".join(p for p in parts if p) or "—"


def _build_address(obj: ObjectModel) -> str:
    parts = []
    if obj.region and obj.region.name:
        parts.append(f"{obj.region.name} {obj.region.spec_region.name}")
    if obj.arial and obj.arial.name:
        parts.append(f"{obj.arial.name} {obj.arial.spec_arial.name}")
    if obj.locality and obj.locality.name:
        prefix = ""
        sl = getattr(obj.locality, "spec_locality", None)
        if sl and getattr(sl, "short_name", None):
            prefix = f"{sl.short_name} "
        parts.append(f"{prefix}{obj.locality.name}".strip())
    if obj.street and obj.street.name:
        prefix = ""
        ss = getattr(obj.street, "spec_street", None)
        if ss and getattr(ss, "short_name", None):
            prefix = f"{ss.short_name} "
        parts.append(f"{prefix}{obj.street.name}".strip())
    if obj.build_number:
        prefix = obj.spec_build.name if obj.spec_build and obj.spec_build.name else "д."
        parts.append(f"{prefix} {obj.build_number}".strip())
    if obj.room_number:
        prefix = obj.spec_room.name if obj.spec_room and obj.spec_room.name else "пом."
        parts.append(f"{prefix} {obj.room_number}".strip())
    return ", ".join(parts) if parts else "—"


def _organization_to_dict(org: Optional[Organization]) -> dict:
    if not org:
        return {"name": "—", "short_name": "—", "job_title": "—", "director_full_name": "—"}
    return {
        "name": org.name or "—",
        "short_name": org.short_name or "—",
        "job_title": (org.spec_job_title.name if getattr(org, "spec_job_title", None) else "—"),
        "director_full_name": _format_director_full_name(org),
    }


def _select_template_name(spec_order_name: Optional[str]) -> str:
    if not spec_order_name:
        raise HTTPException(status_code=400, detail="У заявки не указан тип")
    n = spec_order_name.lower().strip()
    if "планов" in n:
        return "order_planned.html"
    raise HTTPException(
        status_code=501,
        detail=f"Шаблон для типа заявки «{spec_order_name}» пока не реализован",
    )


def _build_equipment_rows(obj: ObjectModel) -> list[dict]:
    rows = []
    for oe in (obj.objects_equipments or []):
        if not oe.equipment:
            continue
        count = oe.count if oe.count is not None else 0
        rows.append({
            "name": oe.equipment.name or "—",
            "count": count,
            "count_planned": count,
        })
    return rows


async def _load_order_with_relations(session, order_id: int) -> Order:
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.spec_order),
            selectinload(Order.contract)
                .selectinload(Contract.customer)
                .selectinload(Organization.spec_job_title),
            selectinload(Order.contract)
                .selectinload(Contract.executor)
                .selectinload(Organization.spec_job_title),
            selectinload(Order.object).selectinload(ObjectModel.region),
            selectinload(Order.object).selectinload(ObjectModel.arial),
            selectinload(Order.object)
                .selectinload(ObjectModel.locality)
                .selectinload(Locality.spec_locality),
            selectinload(Order.object)
                .selectinload(ObjectModel.street)
                .selectinload(Street.spec_street),
            selectinload(Order.object).selectinload(ObjectModel.spec_build),
            selectinload(Order.object).selectinload(ObjectModel.spec_room),
            selectinload(Order.object)
                .selectinload(ObjectModel.objects_equipments)
                .selectinload(Objects_Equipment.equipment),
        )
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail=f"Заявка с id {order_id} не найдена")
    if not order.contract:
        raise HTTPException(status_code=400, detail="У заявки не указан контракт")
    if not order.object:
        raise HTTPException(status_code=400, detail="У заявки не указан объект")
    return order


async def render_order_pdf(order_id: int, current_user: User) -> Tuple[bytes, str]:
    """
    Сформировать PDF акта выполненных работ по заявке.
    Возвращает (pdf_bytes, suggested_filename).
    """
    await check_permission(current_user, "order_read", "формирования PDF по заявке")

    async with new_session() as session:
        order = await _load_order_with_relations(session, order_id)

        spec_order_name = order.spec_order.name if order.spec_order else None
        template_name = _select_template_name(spec_order_name)

        contract = order.contract
        customer = _organization_to_dict(contract.customer)
        executor = _organization_to_dict(contract.executor)

        ctx = {
            "order": {
                "id": order.id,
                "number": order.number,
                "created_at": order.created_at,
                "description": order.description or "",
                "status": order.status,
            },
            "contract": {
                "number": contract.number,
                "date_of_consclusion": contract.date_of_consclusion,
            },
            "contract_date_str": _format_full_date(contract.date_of_consclusion),
            "act_date_full": _format_full_date(order.created_at),
            "work_period_str": _format_work_period(order.created_at),
            "customer": customer,
            "executor": executor,
            "object": {
                "id": order.object.id,
                "name": order.object.name or "—",
                "build_number": order.object.build_number or "",
                "room_number": order.object.room_number or "",
            },
            "object_address": _build_address(order.object),
            "equipment_rows": _build_equipment_rows(order.object),
        }

    template = _jinja_env.get_template(template_name)
    html_str = template.render(**ctx)

    pdf_bytes = HTML(string=html_str, base_url=str(TEMPLATES_DIR)).write_pdf()
    filename = f"act_order_{order_id}.pdf"
    return pdf_bytes, filename


async def render_order_primary_pdf(order_id: int, current_user: User) -> Tuple[bytes, str]:
    """
    Сформировать PDF акта первичного обследования по заявке.
    Дату акта оставляем пустой (заполняется вручную).
    """
    await check_permission(current_user, "order_read", "формирования PDF акта первичного обследования")

    async with new_session() as session:
        order = await _load_order_with_relations(session, order_id)

        contract = order.contract
        customer = _organization_to_dict(contract.customer)
        executor = _organization_to_dict(contract.executor)

        ctx = {
            "order": {
                "id": order.id,
                "number": order.number,
            },
            "contract": {
                "spec_contract": contract.spec_contract.name or "",
                "number": contract.number,
                "subject": contract.subject or "",
                "short_subject": contract.short_subject or "",
                "date_str": _format_full_date(contract.date_of_consclusion),
            },
            "customer": customer,
            "executor": executor,
            "object": {
                "id": order.object.id,
                "name": order.object.name or "—",
            },
            "object_address": _build_address(order.object),
            "equipment_rows": _build_equipment_rows(order.object),
        }

    template = _jinja_env.get_template("order_primary.html")
    html_str = template.render(**ctx)

    pdf_bytes = HTML(string=html_str, base_url=str(TEMPLATES_DIR)).write_pdf()
    filename = f"act_primary_{order_id}.pdf"
    return pdf_bytes, filename
