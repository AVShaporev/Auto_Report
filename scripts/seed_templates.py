"""
Идемпотентно копирует все .docx/.dotx из templates/seeds/ в MEDIA_TEMPLATES_PATH.

Запускать после миграций при первом деплое каждого окружения (stage, prod).
Если файл с таким именем уже есть в storage — не перезаписывает (защита от
случайного отката админских загрузок).

Использование:
  poetry run python scripts/seed_templates.py
"""
from pathlib import Path
import shutil
import sys

# Скрипт лежит в scripts/, а corner-config — в корне.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import MEDIA_TEMPLATES_PATH  # noqa: E402


SEEDS_DIR = ROOT / "templates" / "seeds"


def main() -> int:
    if not SEEDS_DIR.exists():
        print(f"[seed_templates] {SEEDS_DIR} не существует — нечего сидить.", file=sys.stderr)
        return 0

    MEDIA_TEMPLATES_PATH.mkdir(parents=True, exist_ok=True)

    seeded = 0
    skipped = 0
    for src in SEEDS_DIR.iterdir():
        if not src.is_file():
            continue
        if src.suffix.lower() not in {".docx", ".dotx"}:
            continue

        dst = MEDIA_TEMPLATES_PATH / src.name
        if dst.exists():
            print(f"[seed_templates] skip {src.name} — already in storage")
            skipped += 1
            continue

        shutil.copy2(src, dst)
        print(f"[seed_templates] copied {src.name} -> {dst}")
        seeded += 1

    print(f"[seed_templates] done: {seeded} new, {skipped} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
