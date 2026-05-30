"""
Тесты для сложной сущности (Issue) — много FK, отдельный PATCH /status,
RBAC через `issue_*` флаги, валидация бизнес-правил (resolved_date обязателен
для статуса 'resolved').

Эти тесты показывают шаблон для сущностей со зависимостями: используем фикстуру
`reference_data`, которая подготавливает Object → Equipment → Objects_Equipment.
"""

from httpx import AsyncClient

from tests.factories import create_issue


async def test_create_issue_success(
    client: AsyncClient,
    superadmin_token: str,
    superadmin_user: dict,
    auth_headers,
    reference_data,
):
    payload = {
        "title": "Не работает огнетушитель",
        "description": "Сорван опломбированный замок",
        "object_equipment_id": reference_data["objects_equipment"].id,
        "priority_id": reference_data["spec_priority"]["medium"].id,
        "detected_date": "2026-01-15",
        "is_critical": True,
        "assigned_to_id": None,
    }
    resp = await client.post(
        "/api/issue/create", json=payload, headers=auth_headers(superadmin_token)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["priority_id"] == payload["priority_id"]
    assert data["is_critical"] is True
    # Номер генерируется бэком
    assert data["number"]


async def test_create_issue_invalid_priority_returns_400(
    client: AsyncClient, superadmin_token: str, auth_headers, reference_data
):
    """При несуществующем priority_id сервис должен ответить 400, не 500."""
    resp = await client.post(
        "/api/issue/create",
        json={
            "title": "Неисправность",
            "object_equipment_id": reference_data["objects_equipment"].id,
            "priority_id": 99999,
            "detected_date": "2026-01-15",
        },
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 400


async def test_list_issue_filter_by_priority(
    client: AsyncClient,
    superadmin_token: str,
    superadmin_user: dict,
    auth_headers,
    reference_data,
    db_session,
):
    """Проверка фильтра ?priority_id=... — критичен для UI неисправностей."""
    medium = reference_data["spec_priority"]["medium"].id
    high = reference_data["spec_priority"]["high"].id
    new_status_id = reference_data["spec_status"]["new"].id
    oe_id = reference_data["objects_equipment"].id
    reporter_id = superadmin_user["user"].id

    await create_issue(
        db_session, object_equipment_id=oe_id, priority_id=medium,
        status_id=new_status_id, reported_by_id=reporter_id, number="Н-001",
    )
    await create_issue(
        db_session, object_equipment_id=oe_id, priority_id=high,
        status_id=new_status_id, reported_by_id=reporter_id, number="Н-002",
    )
    await create_issue(
        db_session, object_equipment_id=oe_id, priority_id=high,
        status_id=new_status_id, reported_by_id=reporter_id, number="Н-003",
    )

    resp = await client.get(
        f"/api/issue/list?priority_id={high}",
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(item["priority_id"] == high for item in data["items"])


async def test_patch_issue_status_to_resolved_requires_date(
    client: AsyncClient,
    superadmin_token: str,
    superadmin_user: dict,
    auth_headers,
    reference_data,
    db_session,
):
    """
    При переводе в статус с code='resolved' бэк требует `resolved_date`.
    Без даты — 400.
    """
    issue = await create_issue(
        db_session,
        object_equipment_id=reference_data["objects_equipment"].id,
        priority_id=reference_data["spec_priority"]["medium"].id,
        status_id=reference_data["spec_status"]["new"].id,
        reported_by_id=superadmin_user["user"].id,
    )

    resolved_id = reference_data["spec_status"]["resolved"].id
    resp_no_date = await client.patch(
        f"/api/issue/{issue.id}/status",
        json={"status_id": resolved_id},
        headers=auth_headers(superadmin_token),
    )
    assert resp_no_date.status_code == 400

    resp_with_date = await client.patch(
        f"/api/issue/{issue.id}/status",
        json={"status_id": resolved_id, "resolved_date": "2026-02-01"},
        headers=auth_headers(superadmin_token),
    )
    assert resp_with_date.status_code == 200
    data = resp_with_date.json()
    assert data["status_id"] == resolved_id
    assert data["resolved_date"] == "2026-02-01"
