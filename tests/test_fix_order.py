"""Заявка на устранение неисправности (1.0.61–1.0.62) и авто-«Устранена» при
утверждении отчёта по ней (1.0.66).

Сценарий: неисправность «Новая» → POST /api/order/create с issue_id (тип по
умолчанию — системный code='fix') → неисправность «В работе», связь в обе
стороны → отчёт по заявке → PATCH /report/{id}/status «Утверждён» →
неисправность «Устранена» с сегодняшней датой.
"""
from datetime import date

from httpx import AsyncClient
from sqlalchemy import select

from model.issue import Issue
from model.order import Order
from model.report import Report
from model.spec_order import Spec_Order
from model.spec_order_status import Spec_Order_Status
from model.spec_report_status import Spec_Report_Status
from model.spec_status import Spec_Status
from tests.factories import create_issue


async def _seed_fix_order_catalogs(session) -> dict:
    """Справочники, которых нет в bootstrap_minimum_reference_data."""
    in_progress = Spec_Status(name="В работе", code="in_progress")
    fix_type = Spec_Order(name="Устранение неисправности", short_name="РЕМ", code="fix",
                          is_system=True, sla_kind="manual")
    order_new = Spec_Order_Status(name="Новая", is_default=True)
    report_work = Spec_Report_Status(name="В работе", is_default=True)
    report_approved = Spec_Report_Status(name="Утверждён")
    session.add_all([in_progress, fix_type, order_new, report_work, report_approved])
    await session.commit()
    return {"in_progress": in_progress, "fix_type": fix_type,
            "report_work": report_work, "report_approved": report_approved}


async def test_fix_order_then_report_approval_resolves_issue(
    client: AsyncClient,
    db_session,
    superadmin_token: str,
    superadmin_user: dict,
    auth_headers,
    reference_data,
):
    cat = await _seed_fix_order_catalogs(db_session)
    issue = await create_issue(
        db_session,
        object_equipment_id=reference_data["objects_equipment"].id,
        priority_id=reference_data["spec_priority"]["medium"].id,
        status_id=reference_data["spec_status"]["new"].id,
        reported_by_id=superadmin_user["user"].id,
        title="Течь",
    )

    # 1. Заявка на устранение без spec_order_id → системный тип fix
    resp = await client.post("/api/order/create", headers=auth_headers(superadmin_token), json={
        "contract_id": reference_data["contract"].id,
        "object_id": reference_data["object"].id,
        "description": "Устранение неисправности",
        "issue_id": issue.id,
    })
    assert resp.status_code == 200, resp.text
    order = resp.json()
    assert order["spec_order_id"] == cat["fix_type"].id
    assert order["number"].endswith("/РЕМ/1")
    assert [fi["id"] for fi in order["fix_issues"]] == [issue.id]

    resp = await client.get(f"/api/issue/{issue.id}", headers=auth_headers(superadmin_token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["order_id"] == order["id"]
    assert data["order_number"] == order["number"]
    assert data["status_code"] == "in_progress"

    # Вторая заявка на ту же неисправность — 400
    resp = await client.post("/api/order/create", headers=auth_headers(superadmin_token), json={
        "contract_id": reference_data["contract"].id,
        "object_id": reference_data["object"].id,
        "issue_id": issue.id,
    })
    assert resp.status_code == 400
    assert order["number"] in resp.json()["detail"]

    # 2. Отчёт по заявке → утверждение
    report = Report(
        number="ОТЧ-1", status_id=cat["report_work"].id,
        period_id=reference_data["period"].id, contract_id=reference_data["contract"].id,
        object_id=reference_data["object"].id, user_id=superadmin_user["user"].id,
    )
    db_session.add(report)
    await db_session.commit()
    db_order = await db_session.get(Order, order["id"])
    db_order.report_id = report.id
    await db_session.commit()

    resp = await client.patch(
        f"/api/report/{report.id}/status", headers=auth_headers(superadmin_token),
        json={"status_id": cat["report_approved"].id},
    )
    assert resp.status_code == 200, resp.text

    # 3. Неисправность устранена сегодняшней датой (id берём до expire_all —
    # иначе ленивая подгрузка вне greenlet)
    issue_id, resolved_id = issue.id, reference_data["spec_status"]["resolved"].id
    db_session.expire_all()
    fresh = (await db_session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
    assert fresh.is_resolved is True
    assert fresh.status_id == resolved_id
    assert fresh.resolved_date == date.today()


async def test_report_approval_without_fix_orders_changes_nothing(
    client: AsyncClient,
    db_session,
    superadmin_token: str,
    superadmin_user: dict,
    auth_headers,
    reference_data,
):
    """Обычный отчёт (заявки без неисправностей) — утверждение ничего лишнего не трогает."""
    cat = await _seed_fix_order_catalogs(db_session)
    issue = await create_issue(
        db_session,
        object_equipment_id=reference_data["objects_equipment"].id,
        priority_id=reference_data["spec_priority"]["medium"].id,
        status_id=reference_data["spec_status"]["new"].id,
        reported_by_id=superadmin_user["user"].id,
    )
    report = Report(
        number="ОТЧ-2", status_id=cat["report_work"].id,
        period_id=reference_data["period"].id, contract_id=reference_data["contract"].id,
        object_id=reference_data["object"].id, user_id=superadmin_user["user"].id,
    )
    db_session.add(report)
    await db_session.commit()

    resp = await client.patch(
        f"/api/report/{report.id}/status", headers=auth_headers(superadmin_token),
        json={"status_id": cat["report_approved"].id},
    )
    assert resp.status_code == 200, resp.text

    issue_id, new_id = issue.id, reference_data["spec_status"]["new"].id
    db_session.expire_all()
    fresh = (await db_session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
    assert fresh.is_resolved is False
    assert fresh.status_id == new_id
