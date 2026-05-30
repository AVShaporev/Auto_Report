"""
Тесты пагинации/сортировки/поиска.

`PaginationParams` (schema/pagination.py) — общий contract для всех `/list`
эндпоинтов. Достаточно протестировать его на одном представительном эндпоинте,
плюс быстрая sanity-проверка на нескольких других — что contract стабилен.
"""

import pytest
from httpx import AsyncClient

from tests.helpers import assert_paginated_shape


async def _seed_priorities(client, token, auth_headers, count: int):
    """Засеять справочник через API — изолирует тест от прямой работы с БД.

    Прямая запись через `db_session` после уже сделанного API-вызова в том
    же event-loop'е на Windows вызывает asyncpg
    `cannot perform operation: another operation is in progress`,
    поэтому для тестов с предварительным login'ом данные создаём через API.
    """
    for i in range(count):
        resp = await client.post(
            "/api/spec_priority/create",
            json={"name": f"P-{i}", "code": f"code_{i}"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text


async def test_default_pagination_params(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    """Без параметров: page=1, per_page=20, items не пуст если данные есть."""
    await _seed_priorities(client, superadmin_token, auth_headers, 5)

    resp = await client.get(
        "/api/spec_priority/list", headers=auth_headers(superadmin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert_paginated_shape(data)
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert data["total"] == 5
    assert len(data["items"]) == 5


async def test_pagination_respects_per_page(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    await _seed_priorities(client, superadmin_token, auth_headers, 7)

    resp = await client.get(
        "/api/spec_priority/list?per_page=3",
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["per_page"] == 3
    assert data["pages"] == 3  # 7 / 3 = ceil 3
    assert len(data["items"]) == 3


async def test_pagination_second_page(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    await _seed_priorities(client, superadmin_token, auth_headers, 7)

    resp = await client.get(
        "/api/spec_priority/list?per_page=3&page=2",
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert len(data["items"]) == 3


@pytest.mark.parametrize("per_page", [0, 101, -1])
async def test_pagination_invalid_per_page(
    client: AsyncClient, superadmin_token: str, auth_headers, per_page
):
    """`per_page` ограничен (1 <= x <= 100). Любое нарушение → 422."""
    resp = await client.get(
        f"/api/spec_priority/list?per_page={per_page}",
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 422


async def test_pagination_invalid_sort_order(
    client: AsyncClient, superadmin_token: str, auth_headers
):
    """`sort_order` принимает только asc/desc, прочее — 422."""
    resp = await client.get(
        "/api/spec_priority/list?sort_order=upwards",
        headers=auth_headers(superadmin_token),
    )
    assert resp.status_code == 422
