"""
Общие хелперы для тестов API.

Это не «утилиты на все случаи жизни» — только то, что повторяется в
нескольких тестах и читается лучше как именованная функция, чем как inline-выражение.
"""

from typing import Any


def assert_paginated_shape(payload: Any) -> None:
    """
    PaginatedResponse[T] во всех роутерах имеет одну и ту же форму.
    Этот хелпер ловит регрессии (поле переименовали / убрали).
    """
    assert isinstance(payload, dict), f"ожидался dict, получен {type(payload)}"
    for field in ("items", "total", "page", "per_page", "pages"):
        assert field in payload, f"PaginatedResponse: нет поля {field!r}"
    assert isinstance(payload["items"], list)
    assert isinstance(payload["total"], int) and payload["total"] >= 0
    assert isinstance(payload["page"], int) and payload["page"] >= 1
    assert isinstance(payload["per_page"], int) and payload["per_page"] >= 1
    assert isinstance(payload["pages"], int) and payload["pages"] >= 0


def assert_options_shape(payload: Any) -> None:
    """`/options` всегда отдаёт List[{id, name}] (+ опц. поля)."""
    assert isinstance(payload, list)
    for item in payload:
        assert isinstance(item, dict)
        assert "id" in item and isinstance(item["id"], int)
        assert "name" in item and isinstance(item["name"], str)
