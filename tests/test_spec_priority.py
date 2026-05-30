"""
Полный CRUD-цикл для простого справочника (spec_priority).

Эта же модель тестов применима к любому Spec_* — достаточно поменять путь
и payload-шаблон. Если у вас будут отдельные тесты на каждый справочник —
используйте этот файл как образец.
"""

from httpx import AsyncClient

from tests.helpers import assert_paginated_shape, assert_options_shape


# --------------------- CREATE ---------------------

async def test_create_spec_priority_success(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    payload = {"name": "Низкий", "code": "low", "description": "не критично"}
    resp = await client.post(
        "/api/spec_priority/create", json=payload, headers=auth_headers(superadmin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"]
    assert data["name"] == "Низкий"
    assert data["code"] == "low"
    assert data["description"] == "не критично"


async def test_create_spec_priority_duplicate_code(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    """code в `spec_prioritys.code` UNIQUE — дубликат → 400/409."""
    await client.post(
        "/api/spec_priority/create",
        json={"name": "Низкий", "code": "low"},
        headers=auth_headers(superadmin_token),
    )
    resp = await client.post(
        "/api/spec_priority/create",
        json={"name": "Дубль", "code": "low"},
        headers=auth_headers(superadmin_token),
    )
    # Сервис возвращает 400 (Duplicate). Если поменяется на 409 — поправить
    # этот тест, а не код: 409 семантически точнее.
    assert resp.status_code in (400, 409)


# --------------------- READ ---------------------

async def test_get_spec_priority_by_id(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    create_resp = await client.post(
        "/api/spec_priority/create",
        json={"name": "Средний", "code": "medium"},
        headers=auth_headers(superadmin_token),
    )
    new_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/spec_priority/{new_id}", headers=auth_headers(superadmin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == new_id
    assert data["code"] == "medium"


async def test_get_spec_priority_not_found(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    resp = await client.get(
        "/api/spec_priority/9999", headers=auth_headers(superadmin_token)
    )
    assert resp.status_code == 404


async def test_list_spec_priority(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    for i, code in enumerate(["low", "medium", "high"]):
        await client.post(
            "/api/spec_priority/create",
            json={"name": f"P{i}", "code": code},
            headers=auth_headers(superadmin_token),
        )

    resp = await client.get(
        "/api/spec_priority/list", headers=auth_headers(superadmin_token)
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert_paginated_shape(payload)
    assert payload["total"] == 3


async def test_options_spec_priority(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    for code in ("low", "medium", "high"):
        await client.post(
            "/api/spec_priority/create",
            json={"name": code, "code": code},
            headers=auth_headers(superadmin_token),
        )

    resp = await client.get(
        "/api/spec_priority/options", headers=auth_headers(superadmin_token)
    )
    assert resp.status_code == 200
    assert_options_shape(resp.json())


# --------------------- UPDATE ---------------------

async def test_update_spec_priority(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    create_resp = await client.post(
        "/api/spec_priority/create",
        json={"name": "Низкий", "code": "low"},
        headers=auth_headers(superadmin_token),
    )
    new_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/spec_priority/{new_id}",
        json={"description": "не критично"},
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "не критично"
    # Не присланные поля не должны затереться (model_dump(exclude_unset=True))
    assert data["name"] == "Низкий"
    assert data["code"] == "low"


# --------------------- DELETE ---------------------

async def test_delete_spec_priority(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    create_resp = await client.post(
        "/api/spec_priority/create",
        json={"name": "Удалить", "code": "to_delete"},
        headers=auth_headers(superadmin_token),
    )
    new_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/spec_priority/{new_id}", headers=auth_headers(superadmin_token)
    )
    assert resp.status_code == 200

    # Подтверждение — повторный GET → 404
    resp_get = await client.get(
        f"/api/spec_priority/{new_id}", headers=auth_headers(superadmin_token)
    )
    assert resp_get.status_code == 404
