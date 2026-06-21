"""
scripts/_perf_audit.py — агрегатор SQL-counter логов для perf-аудита.

Читает JSONL-логи Loguru с полями sql_count / sql_time_sec / sql_top (их
пишет middleware sql_counter — см. utils/sql_counter.py и middleware.py),
агрегирует по нормализованному пути endpoint'а ({id} вместо чисел),
выводит топ-15 по avg_SQL.

Используется для замера эффекта Phase B performance-оптимизации:
запустить ДО изменений (baseline), сделать фазу, прокликать те же
страницы, запустить снова — сравнить таблицы.

Префикс `_` в имени файла — отметка «временный отладочный, удалить
после закрытия Phase B».

Пример:
    poetry run python scripts/_perf_audit.py logs/logs_15.06.2026-21.06.2026.json
    poetry run python scripts/_perf_audit.py logs/logs_15.06.2026-21.06.2026.json --top 30
"""

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def norm_path(p):
    return "/".join("{id}" if s.isdigit() else s for s in (p or "").split("/"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_file", type=Path, help="путь к logs_*.json")
    parser.add_argument("--top", type=int, default=15, help="сколько endpoint'ов в топе")
    parser.add_argument("--with-top-sql", action="store_true",
                        help="показать топ-5 SQL-повторов для каждого endpoint'а")
    args = parser.parse_args()

    http = []
    with open(args.log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("kind") != "http" or e.get("sql_count") is None:
                continue
            http.append(e)

    agg = defaultdict(lambda: {"hits": 0, "dur": [], "sql": [], "sql_time": [], "top": Counter()})
    for e in http:
        k = "{} {}".format(e["method"], norm_path(e["path"]))
        a = agg[k]
        a["hits"] += 1
        a["dur"].append(e["duration_sec"])
        a["sql"].append(e["sql_count"])
        a["sql_time"].append(e.get("sql_time_sec", 0))
        for q in e.get("sql_top") or []:
            a["top"][q["sql"]] += q["count"]

    print("Записей: {}".format(len(http)))
    print()
    header = "{:<50} {:>5} {:>8} {:>8} {:>8} {:>8}".format(
        "endpoint", "hits", "avg_SQL", "max_SQL", "avg_dur", "avg_DB"
    )
    print(header)
    rows = [
        (k, a["hits"], statistics.mean(a["sql"]), max(a["sql"]),
         statistics.mean(a["dur"]), statistics.mean(a["sql_time"]), a["top"])
        for k, a in agg.items() if a["hits"] >= 2
    ]
    top_rows = sorted(rows, key=lambda r: r[2], reverse=True)[:args.top]
    for r in top_rows:
        print("{:<50} {:>5} {:>7.1f}  {:>7}  {:>6.2f}s  {:>6.2f}s".format(
            r[0], r[1], r[2], r[3], r[4], r[5]
        ))

    if args.with_top_sql:
        print()
        print("=== Топ-5 SQL-повторов на endpoint ===")
        for r in top_rows[:5]:
            ep, hits, avg_s, max_s, avg_d, avg_db, top = r
            print("\n>>> {} hits={} avg_SQL={:.0f} max={} avg_dur={:.2f}s".format(
                ep, hits, avg_s, max_s, avg_d
            ))
            for q, n in top.most_common(5):
                print("  {}x {}".format(n, q[:130]))


if __name__ == "__main__":
    main()
