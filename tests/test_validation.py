"""
Тесты валидации входных данных (Pydantic v2).

Цель — убедиться, что:
  - При нарушении constraint'ов схемы возвращается 422 (а не 500/200).
  - Ошибки приходят в стандартном формате FastAPI (`detail` со списком).

Берём один представительный POST/PUT эндпоинт. Для других схем можно
использовать ту же модель тестов, переиспользуя `@parametrize`.
"""

from httpx import AsyncClient


async def test_create_spec_priority_missing_required_field(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    """Без `name` — 422 от Pydantic."""
    resp = await client.post(
        "/api/spec_priority/create",
        json={"code": "low"},
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body
    assert any(err["loc"][-1] == "name" for err in body["detail"])


async def test_create_spec_priority_name_too_short(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    """`name` имеет min_length=2 — 1 символ → 422."""
    resp = await client.post(
        "/api/spec_priority/create",
        json={"name": "x", "code": "x1"},
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 422


async def test_create_spec_priority_code_too_long(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    """`code` имеет max_length=50 — превышение → 422."""
    resp = await client.post(
        "/api/spec_priority/create",
        json={"name": "Нормальное имя", "code": "x" * 51},
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 422


async def test_extra_fields_are_ignored_or_rejected(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    """
    Лишние поля в payload — Pydantic v2 по умолчанию игнорирует.
    Тест фиксирует текущее поведение, чтобы изменение конфигурации схемы
    (extra='forbid') было замечено и осознанно.
    """
    resp = await client.post(
        "/api/spec_priority/create",
        json={
            "name": "Низкий",
            "code": "low_test",
            "this_field_does_not_exist": "noise",
        },
        headers=auth_headers(superadmin_token),
    )
    # Сейчас extra='ignore' (default), поэтому ожидаем 200.
    # Если потом включат extra='forbid' — этот тест поможет вспомнить, что
    # фронт может отсылать "лишние" поля и сломается.
    assert resp.status_code == 200
