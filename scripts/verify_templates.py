"""
Проверка состояния шаблонов документов: что прописано в БД и что реально лежит на диске.

Не требует логина — читает БД и файловую систему напрямую через config.py + модели.

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
from config import MEDIA_PATH, MEDIA_TEMPLATES_PATH  # noqa: E402


async def main() -> int:
    async with new_session() as session:
        result = await session.execute(select(Spec_Order).order_by(Spec_Order.id))
        items = result.scalars().all()

    print(f"MEDIA_PATH:            {MEDIA_PATH}")
    print(f"MEDIA_TEMPLATES_PATH:  {MEDIA_TEMPLATES_PATH}")
    print(f"Папка существует:       {MEDIA_TEMPLATES_PATH.exists()}")
    print()

    headers = ["id", "code", "name", "is_sys", "template_filename", "storage_path", "file_exists"]
    widths = [4, 12, 22, 6, 32, 35, 11]

    def row(values):
        cells = []
        for v, w in zip(values, widths):
            s = "" if v is None else str(v)
            if len(s) > w:
                s = s[: w - 1] + "…"
            cells.append(s.ljust(w))
        return "  ".join(cells)

    print(row(headers))
    print(row(["-" * w for w in widths]))

    for it in items:
        if it.template_storage_path:
            abs_path = MEDIA_PATH / it.template_storage_path
            file_ok = "YES" if abs_path.exists() else "MISSING"
        else:
            file_ok = "—"
        print(row([
            it.id,
            it.code,
            it.name,
            "YES" if it.is_system else "",
            it.template_filename,
            it.template_storage_path,
            file_ok,
        ]))

    print()

    # Сверим, есть ли в storage файлы, на которые никто из spec_orders не ссылается.
    if MEDIA_TEMPLATES_PATH.exists():
        on_disk = {p.name for p in MEDIA_TEMPLATES_PATH.iterdir() if p.is_file()}
        referenced = {
            Path(it.template_storage_path).name for it in items if it.template_storage_path
        }
        orphans = on_disk - referenced
        if orphans:
            print(f"[WARN] Файлы в storage без ссылки из БД: {sorted(orphans)}")
        else:
            print("[OK]   Лишних файлов в storage нет")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
