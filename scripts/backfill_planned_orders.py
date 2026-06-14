"""
Ручной бэкфилл авто-заявок для существующих объектов.

Используется один раз после миграции e7c2a5d1f3b8 на каждом env (stage, prod, VDS prod),
чтобы для уже созданных объектов появились:
- «Первичное обследование» (если ещё нет ни одной заявки с is_default_primary-типом);
- «Плановое ТО» за текущий период (через tick_planned_orders).

Идемпотентность:
- primary создаётся только если для объекта нет ни одной заявки с
  spec_order.is_default_primary=TRUE;
- planned делегируется в tick_planned_orders — там идёт SELECT по
  (object_id, spec_order_id, period_start_date), дубль не появится.

Если в spec_orders не выставлен ни один is_default_*-флаг — скрипт
отчитывается и выходит без изменений.

Использование (после применения миграций):
  poetry run python scripts/backfill_planned_orders.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Скрипт лежит в scripts/, корень проекта — на уровень выше.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from datetime import date  # noqa: E402

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from database.database import new_session  # noqa: E402
from model.contract import Contract  # noqa: E402
from model.object import Object as ObjectModel  # noqa: E402
from model.order import Order  # noqa: E402
from model.spec_order import Spec_Order  # noqa: E402
from service.order_autogen import (  # noqa: E402
    _create_order,
    _get_default_spec_order,
    _get_system_user_id,
    tick_planned_orders,
)


async def _backfill_primary_orders() -> dict:
    """Создать primary-заявку каждому объекту, у которого её ещё нет."""
    stats = {"created": 0, "skipped_exists": 0, "errors": []}

    async with new_session() as cfg_session:
        primary_spec = await _get_default_spec_order(cfg_session, primary=True)
        if primary_spec is None:
            stats["errors"].append(
                "В spec_orders нет записи с is_default_primary=TRUE — "
                "primary не создаём."
            )
            return stats
        primary_spec_id = primary_spec.id

        try:
            system_user_id = await _get_system_user_id(cfg_session)
        except Exception as e:  # noqa: BLE001
            stats["errors"].append(f"system-user: {e}")
            return stats

    # Список id всех объектов.
    async with new_session() as session:
        ids = (
            await session.execute(select(ObjectModel.id).order_by(ObjectModel.id))
        ).scalars().all()

    today = date.today()

    for object_id in ids:
        try:
            async with new_session() as session:
                # Есть ли уже primary-заявка у этого объекта?
                exists_q = (
                    select(Order.id)
                    .where(
                        Order.object_id == object_id,
                        Order.spec_order_id == primary_spec_id,
                    )
                    .limit(1)
                )
                if (await session.execute(exists_q)).scalar_one_or_none() is not None:
                    stats["skipped_exists"] += 1
                    continue

                stmt = (
                    select(ObjectModel)
                    .where(ObjectModel.id == object_id)
                    .options(
                        selectinload(ObjectModel.contract).selectinload(Contract.customer),
                        selectinload(ObjectModel.period),
                    )
                )
                obj = (await session.execute(stmt)).scalar_one_or_none()
                if obj is None:
                    continue
                if obj.contract is None:
                    stats["errors"].append(f"object_id={object_id}: нет договора")
                    continue

                primary_spec = await session.get(Spec_Order, primary_spec_id)
                await _create_order(
                    session,
                    obj=obj,
                    spec_order=primary_spec,
                    system_user_id=system_user_id,
                    today=today,
                    period_start_date=None,
                    description="Backfill: первичное обследование (бэкфилл существующего объекта).",
                )
                await session.commit()
                stats["created"] += 1
        except Exception as e:  # noqa: BLE001
            stats["errors"].append(f"object_id={object_id}: {type(e).__name__}: {e}")

    return stats


async def _amain() -> int:
    print("[backfill] Старт авто-генерации заявок для существующих объектов.")
    print(f"[backfill] Сегодня: {date.today().isoformat()}")

    # 1) primary — добиваем первичные обследования.
    print("[backfill] Шаг 1/2: первичные обследования…")
    primary_stats = await _backfill_primary_orders()
    print(
        f"[backfill] primary: создано={primary_stats['created']}, "
        f"уже было={primary_stats['skipped_exists']}, "
        f"ошибок={len(primary_stats['errors'])}"
    )
    for err in primary_stats["errors"]:
        print(f"  [primary] {err}", file=sys.stderr)

    # 2) planned — через tick для текущего периода.
    print("[backfill] Шаг 2/2: плановые ТО (через tick)…")
    tick_result = await tick_planned_orders()
    print(f"[backfill] {tick_result.summary()}")
    for err in tick_result.errors:
        print(f"  [planned] {err}", file=sys.stderr)

    # Exit-code 1, если были ошибки — удобно ловить в CI-пайплайне.
    had_errors = bool(primary_stats["errors"]) or bool(tick_result.errors)
    if had_errors:
        print("[backfill] Завершено с ошибками — см. stderr.", file=sys.stderr)
        return 1
    print("[backfill] Готово.")
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    sys.exit(main())
