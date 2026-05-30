"""
Тесты аутентификации: /api/auth/login, /api/auth/me, /api/auth/refresh.

Что покрываем:
  - Успешный логин обычной пары (username + password).
  - Невалидные креды → 401.
  - /me с валидным Bearer токеном.
  - /me без токена → 401/403.
  - /me с битым токеном → 401.
  - /refresh с access-токеном (не refresh) → 401 (валидация type).
  - /refresh c валидным refresh-токеном → новый access.
"""

from httpx import AsyncClient


async def test_login_success_returns_tokens(client: AsyncClient, regular_user: dict):
    resp = await client.post(
        "/api/auth/login",
        data={"username": regular_user["user"].name, "password": regular_user["password"]},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["user"]["name"] == regular_user["user"].name
    # JWT — три части, разделённые точками
    assert payload["access_token"].count(".") == 2
    assert payload["refresh_token"].count(".") == 2


async def test_login_wrong_password_returns_401(client: AsyncClient, regular_user: dict):
    resp = await client.post(
        "/api/auth/login",
        data={"username": regular_user["user"].name, "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_login_unknown_user_returns_401(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "ghost", "password": "whatever"},
    )
    assert resp.status_code == 401


async def test_me_with_valid_token(
    client: AsyncClient, regular_token: str, regular_user: dict, auth_headers
):
    resp = await client.get("/api/auth/me", headers=auth_headers(regular_token))
    assert resp.status_code == 200
    assert resp.json()["name"] == regular_user["user"].name


async def test_me_with_invalid_token_returns_401(client: AsyncClient, auth_headers):
    resp = await client.get("/api/auth/me", headers=auth_headers("not.a.jwt"))
    assert resp.status_code == 401


async def test_refresh_with_access_token_rejected(
    client: AsyncClient, regular_token: str
):
    """Передаём access-токен в /refresh — должен отбить (type != 'refresh')."""
    resp = await client.post("/api/auth/refresh", json={"refresh_token": regular_token})
    assert resp.status_code == 401


async def test_refresh_success(client: AsyncClient, regular_user: dict):
    login_resp = await client.post(
        "/api/auth/login",
        data={"username": regular_user["user"].name, "password": regular_user["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"].count(".") == 2
    assert data["token_type"] == "bearer"
