# syntax=docker/dockerfile:1.7
#
# Auto_Report backend — multi-stage Docker image
#
# Architecture:
#   Stage 1 (builder): Poetry разворачивает зависимости в requirements.txt.
#     Так в runtime не таскается ни Poetry, ни кеш виртуальных env'ов.
#   Stage 2 (runtime): python:3.11-slim + системные либы + pip install + код.
#
# Размер итогового образа ~ 750-850 MB.
# Основной вклад — LibreOffice (~400 MB), без него .docx → .pdf конверсия не работает.

# =====================================================================
# Stage 1: builder
# =====================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /build

# Poetry 1.8.x — последняя стабильная 1.x.
# 2.x перестроил CLI (poetry export → плагин), не рискуем переходом сейчас.
RUN pip install --no-cache-dir poetry==1.8.5

COPY pyproject.toml poetry.lock ./

# `--without dev`         — без pytest/httpx, они только для локальных тестов.
# `--without-hashes`      — pip на runtime может видеть чуть другие транзитивные версии,
#                           хэши тогда не сходятся и blocks install. На приватный prod-VDS
#                           проверка хэшей — оверкилл; lockfile уже фиксирует версии.
RUN poetry export -f requirements.txt --output requirements.txt \
        --without-hashes --without dev


# =====================================================================
# Stage 2: runtime
# =====================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Системные зависимости:
#   curl                  — HEALTHCHECK дёргает /openapi.json
#   ca-certificates       — TLS-trust (исходящие HTTPS из бэка)
#   tini                  — корректный PID 1, передаёт SIGTERM подпроцессу uvicorn
#   libpango-1.0-0,
#   libpangoft2-1.0-0,
#   libharfbuzz0b         — WeasyPrint (HTML → PDF в order_pdf.py)
#   libreoffice-core,
#   libreoffice-writer    — soffice --headless --convert-to pdf (render_docx.py)
#   fonts-dejavu,
#   fonts-liberation,
#   fonts-noto-core       — без них soffice кладёт tofu вместо кириллицы в PDF
#
# --no-install-recommends срезает cups, dbus, x11-* — сэкономили ~100 MB.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        tini \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libreoffice-core \
        libreoffice-writer \
        fonts-dejavu \
        fonts-liberation \
        fonts-noto-core \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Непривилегированный юзер с реальной HOME (LibreOffice пишет ~/.config/libreoffice
# при старте даже в headless-режиме).
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app

WORKDIR /app

# Зависимости — отдельным слоем (меняются реже кода → лучше docker layer cache).
COPY --from=builder /build/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Код приложения. `.dockerignore` отсекает .env, .git, tests, media, logs.
COPY --chown=app:app . /app

# Entrypoint.sh лежит в docker/ — копируем явно в /entrypoint.sh для удобства.
COPY --chown=app:app docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Pre-create runtime-каталоги, которые named-volume'ы mount'ят сверху.
# Поведение Docker: при первом mount'е ПУСТОГО named volume на каталог
# в образе содержимое каталога копируется в volume, СОХРАНЯЯ ownership.
# Без этого config.py:31 пытается mkdir в /app/media (root-owned volume),
# PermissionError для USER app.
# media/templates — для шаблонов .docx/.dotx, logs — для loguru.
RUN mkdir -p /app/media/templates /app/logs && \
    chown -R app:app /app/media /app/logs

USER app

EXPOSE 8000

# /api/health — лёгкий JSON-ответ FastAPI без аутентификации/БД.
# Тот же endpoint используется GHA deploy-vds.yml для внешней проверки.
# start-period 30s — даёт время на `alembic upgrade head` при первом старте.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health > /dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
