"""Расчёт due_date для Order по SLA-правилам Spec_Order.

Одна публичная функция — `compute_due_date`. Вызывается:
- `service/order.py` при create/update ручных заявок (если due_date не
  передан явно клиентом).
- `service/order_autogen.py` при автогенерации плановых заявок.

Логика (миграция f5c6d7e8f9a0 фиксирует тот же алгоритм в SQL-виде):
    spec_order.sla_kind = 'periodic'
        → конец календарного периода, содержащего anchor:
          period_start_date (если есть — auto-planned) или created_at.
          Period-code берётся у объекта (obj.period.code): monthly /
          quarterly / semiannual / yearly.
    spec_order.sla_kind = 'from_creation'
        → created_at + spec_order.sla_days.
    spec_order.sla_kind = 'manual'
        → None (пользователь заполняет вручную в форме).

Все зависимости (Object.period, Spec_Order.sla_*) — уже загруженные
поля, функция синхронная. Загрузку relationship'ов — на сервис.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Optional


def _period_end(period_code: Optional[str], anchor: date) -> Optional[date]:
    """Конец календарного периода, содержащего дату `anchor`."""
    if not period_code or period_code == 'custom':
        return None
    if period_code == 'monthly':
        last = monthrange(anchor.year, anchor.month)[1]
        return date(anchor.year, anchor.month, last)
    if period_code == 'quarterly':
        q_end_month = ((anchor.month - 1) // 3) * 3 + 3
        last = monthrange(anchor.year, q_end_month)[1]
        return date(anchor.year, q_end_month, last)
    if period_code == 'semiannual':
        if anchor.month <= 6:
            return date(anchor.year, 6, 30)
        return date(anchor.year, 12, 31)
    if period_code == 'yearly':
        return date(anchor.year, 12, 31)
    return None


def _add_workdays(start: date, days: int) -> date:
    """Прибавить N рабочих дней (пропускаем сб/вс).

    Пример: пт + 3 рабочих дня = ср (пт → пн → вт → ср).
    Госпраздники не учитываем — простой вариант без внешнего справочника.
    """
    d = start
    remaining = days
    while remaining > 0:
        d = d + timedelta(days=1)
        if d.weekday() < 5:  # 0..4 = Mon..Fri
            remaining -= 1
    return d


def compute_due_date(
    *,
    sla_kind: str,
    sla_days: Optional[int],
    created_at: date,
    period_start_date: Optional[date] = None,
    period_code: Optional[str] = None,
    sla_days_workdays: bool = False,
) -> Optional[date]:
    """Посчитать срок исполнения заявки по правилам её типа.

    Возвращает None, если правило не применимо (manual или недостаточно
    данных: periodic без period_code, from_creation без sla_days).

    Для 'from_creation' с sla_days_workdays=True — прибавляем рабочие
    дни (пропускаем сб/вс), иначе календарные.
    """
    if sla_kind == 'periodic':
        anchor = period_start_date or created_at
        return _period_end(period_code, anchor)

    if sla_kind == 'from_creation' and sla_days:
        if sla_days_workdays:
            return _add_workdays(created_at, sla_days)
        return created_at + timedelta(days=sla_days)

    # 'manual' и всё что не подходит → None
    return None
