"""
Проверка состояния шаблонов документов: что прописано в БД и что реально лежит на диске.

Не требует логина — читает БД и файловую систему напрямую через config.py + модели.

Показывает два справочника: spec_orders (типы заявок) и spec_journals (виды журналов).

Использование (на сервере под юзером autoreport, с прогруженным env-файлом):
  sudo -u autoreport bash -lc 'set -a && source /etc/autoreport/stage.env && set +a && cd /opt/autoreport/stage/backend && poetry run python scripts/verify_templates.py'
"""
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from database.database import new_session  # noqa: E402
from model.spec_order import Spec_Order  # noqa: E402
from model.spec_journal import Spec_Journal  # noqa: E402
from config import MEDIA_PATH, MEDIA_TEMPLATES_PATH  # noqa: E402


HEADERS = ["id", "code", "name", "is_sys", "template_filename", "storage_path", "file_exists"]
WIDTHS = [4, 12, 36, 6, 32, 35, 11]


def _row(values):
    cells = []
    for v, w in zip(values, WIDTHS):
        s = "" if v is None else str(v)
        if len(s) > w:
            s = s[: w - 1] + "…"
        cells.append(s.ljust(w))
    return "  ".join(cells)


def _print_table(title: str, items) -> set[str]:
    """Печатает таблицу по items, возвращает множество имён файлов, на которые ссылается БД."""
    print(f"== {title} ==")
    print(_row(HEADERS))
    print(_row(["-" * w for w in WIDTHS]))

    referenced: set[str] = set()
    for it in items:
        if it.template_storage_path:
            abs_path = MEDIA_PATH / it.template_storage_path
            file_ok = "YES" if abs_path.exists() else "MISSING"
            referenced.add(Path(it.template_storage_path).name)
        else:
            file_ok = "—"
        print(_row([
            it.id,
            it.code,
            it.name,
            "YES" if it.is_system else "",
            it.template_filename,
            it.template_storage_path,
            file_ok,
        ]))
    print()
    return referenced


async def main() -> int:
    async with new_session() as session:
        orders_result = await session.execute(select(Spec_Order).order_by(Spec_Order.id))
        orders = orders_result.scalars().all()

        journals_result = await session.execute(select(Spec_Journal).order_by(Spec_Journal.id))
        journals = journals_result.scalars().all()

    print(f"MEDIA_PATH:            {MEDIA_PATH}")
    print(f"MEDIA_TEMPLATES_PATH:  {MEDIA_TEMPLATES_PATH}")
    print(f"Папка существует:       {MEDIA_TEMPLATES_PATH.exists()}")
    print()

    ref_orders = _print_table("spec_orders (типы заявок)", orders)
    ref_journals = _print_table("spec_journals (виды журналов)", journals)

    referenced = ref_orders | ref_journals

    if MEDIA_TEMPLATES_PATH.exists():
        on_disk = {p.name for p in MEDIA_TEMPLATES_PATH.iterdir() if p.is_file()}
        orphans = on_disk - referenced
        if orphans:
            print(f"[WARN] Файлы в storage без ссылки из БД: {sorted(orphans)}")
        else:
            print("[OK]   Лишних файлов в storage нет")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
