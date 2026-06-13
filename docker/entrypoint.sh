#!/bin/sh
# Auto_Report backend entrypoint.
#
# Запускается как PID 2 под tini (PID 1) внутри контейнера.
#
# Что делает по порядку:
#   1) Если в /run/secrets/ лежат файлы (Docker secrets, опционально),
#      экспортирует их содержимое в env как ИМЯ_В_КАПСЕ. На .env-варианте
#      директория пустая — шаг no-op.
#   2) Накатывает миграции (`alembic upgrade head`). Alembic читает DB_*
#      из env (через config.py + Pydantic Settings).
#   3) Запускает uvicorn с фиксированными параметрами:
#        --workers 1                — на VDS 1 vCPU, борьба за CPU не нужна.
#        --proxy-headers            — доверяем X-Forwarded-* от frontend-nginx
#                                     (заходит из docker-сети, не из public).
#        --forwarded-allow-ips='*'  — публичный фильтр уже сделал Caddy на хосте.
#
# `set -e` — любая команда с кодом ≠0 кладёт entrypoint, контейнер падает,
#            docker-compose restart: unless-stopped поднимает заново.

set -e

# --- 1. Docker secrets (опциональная подача через /run/secrets/) ---
if [ -d /run/secrets ]; then
    for f in /run/secrets/*; do
        [ -f "$f" ] || continue
        name=$(basename "$f" | tr '[:lower:]' '[:upper:]')
        # shellcheck disable=SC3045
        export "$name"="$(cat "$f")"
    done
fi

# --- 2. Миграции ---
echo "[entrypoint] alembic upgrade head"
alembic upgrade head

# --- 3. Uvicorn ---
echo "[entrypoint] starting uvicorn on 0.0.0.0:8000 (workers=1)"
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='*'
