"""
Smoke-тесты: приложение поднимается, базовые роуты доступны.

Если эти тесты падают, остальное прогонять бессмысленно — что-то сломано на
уровне импортов или регистрации роутеров.
"""

from httpx import AsyncClient


async def test_openapi_schema_available(client: AsyncClient):
    """OpenAPI-схема должна формироваться без ошибок и содержать наши теги."""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["info"]["title"] == "AutoReport API"
    # Базовые роутеры должны быть в схеме
    paths = data["paths"]
    assert "/api/auth/login" in paths
    assert "/api/user/list" in paths


async def test_docs_endpoint(client: AsyncClient):
    """Swagger UI отдаётся (доступность /docs)."""
    resp = await client.get("/docs")
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower()


async def test_protected_route_requires_auth(client: AsyncClient):
    """Случайный защищённый роут без токена → 401/403, а не 500."""
    resp = await client.get("/api/auth/me")
    # HTTPBearer возвращает 403 при отсутствии заголовка (FastAPI default).
    assert resp.status_code in (401, 403)
