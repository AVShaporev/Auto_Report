"""
Тесты RBAC (role-based access control).

Принцип:
  - Сервис требует точные права (`object_read`, `user_create`, ...).
  - У пользователя без флага должен возвращаться 403, а не 500.
  - У суперадмина — должно работать всё.

Покрываем самые «горячие» эндпоинты разных доменов.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.parametrize(
    "method,url",
    [
        ("GET", "/api/user/list"),
        ("GET", "/api/object/list"),
        ("GET", "/api/spec_priority/list"),
        ("GET", "/api/issue/list"),
        ("GET", "/api/role/list"),
    ],
)
async def test_list_requires_read_permission_for_regular_user(
    client: AsyncClient, regular_token: str, auth_headers, method, url
):
    """Обычный пользователь без *_read получает 403 на /list."""
    resp = await client.request(method, url, headers=auth_headers(regular_token))
    assert resp.status_code == 403, f"{method} {url}: ожидал 403, получил {resp.status_code}"


@pytest.mark.parametrize(
    "method,url",
    [
        ("GET", "/api/user/list"),
        ("GET", "/api/object/list"),
        ("GET", "/api/spec_priority/list"),
        ("GET", "/api/issue/list"),
    ],
)
async def test_list_works_for_superadmin(
    client: AsyncClient, superadmin_token: str, auth_headers, reference_data, method, url
):
    """Суперадмин получает 200 на тех же эндпоинтах."""
    resp = await client.request(method, url, headers=auth_headers(superadmin_token))
    assert resp.status_code == 200, f"{method} {url}: получил {resp.status_code}: {resp.text}"


async def test_no_token_returns_401_or_403(client: AsyncClient):
    """Без Authorization-заголовка — отбой на стадии HTTPBearer."""
    resp = await client.get("/api/user/list")
    assert resp.status_code in (401, 403)


async def test_malformed_bearer_token(client: AsyncClient, auth_headers):
    """Authorization: Bearer garbage → 401."""
    resp = await client.get("/api/user/list", headers=auth_headers("garbage"))
    assert resp.status_code == 401
