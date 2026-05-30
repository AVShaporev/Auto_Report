"""
Тесты CRUD-эндпоинтов /api/user.

Закрываем основные сценарии:
  - list + пагинация (форма ответа уже проверена в test_pagination,
    тут — что данные привязаны к роли и поле `role` приходит).
  - get_by_id с правами.
  - get_by_id 404.
  - модификация прав (user_modify) и проверка эффекта.
"""

from httpx import AsyncClient

from tests.helpers import assert_paginated_shape


async def test_user_list_returns_role_object(
    client: AsyncClient,
    superadmin_token: str,
    auth_headers,
    regular_user: dict,
):
    """
    `/user/list` отдаёт `UserResponse`, в нём вложен `role: RoleSimpleResponse`
    с флагами `is_admin/is_superadmin` — фронт использует это для
    фильтрации списка ответственных в IssueForm.
    """
    resp = await client.get(
        "/api/user/list", headers=auth_headers(superadmin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert_paginated_shape(data)
    # Среди items должен быть наш regular_user
    targets = [u for u in data["items"] if u["name"] == regular_user["user"].name]
    assert len(targets) == 1
    target = targets[0]
    assert "role" in target and target["role"] is not None
    assert "is_admin" in target["role"]
    assert "is_superadmin" in target["role"]
    assert target["role"]["is_admin"] is False
    assert target["role"]["is_superadmin"] is False
