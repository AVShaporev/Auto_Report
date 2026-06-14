#!/usr/bin/env bash
# Auto_Report VDS deploy script.
#
# Лежит в git под scripts/deploy_vds.sh.
# На VDS нужно один раз скопировать его в /opt/auto-report/scripts/deploy.sh
# (см. CHEATSHEET в комментарии ниже).
#
# Используется из GitHub Actions:
#   .github/workflows/deploy-vds.yml в Auto_Report репо  → ./deploy.sh backend
#   .github/workflows/deploy-vds.yml в Auto_report_front → ./deploy.sh frontend
# А также вручную с VDS:
#   /opt/auto-report/scripts/deploy.sh all       # обновить оба + пересобрать всё
#   /opt/auto-report/scripts/deploy.sh backend   # обновить только бэк
#   /opt/auto-report/scripts/deploy.sh frontend  # обновить только фронт
#
# Что делает:
#   1. flock — сериализует одновременные деплои бэка и фронта.
#   2. git fetch + reset --hard origin/prod в нужных репо.
#   3. pg_dump в /opt/auto-report/backups/pre-deploy-TS.sql.gz (если postgres жив).
#   4. docker compose up -d --build <service>.
#   5. docker image prune -f.
#   6. Чистит pre-deploy бэкапы старше 14 дней.
#
# ───── INITIAL SETUP CHEATSHEET (один раз на VDS под deploy-юзером) ─────
#   sudo mkdir -p /opt/auto-report/{scripts,backups}
#   sudo chown -R deploy:deploy /opt/auto-report
#   cd /opt/auto-report
#   git clone git@github.com:AVShaporev/Auto_Report.git
#   git clone git@github.com:AVShaporev/Auto_report_front.git
#   cd Auto_Report && git checkout prod && cd ..
#   cd Auto_report_front && git checkout prod && cd ..
#   cp Auto_Report/scripts/deploy_vds.sh scripts/deploy.sh
#   chmod +x scripts/deploy.sh
#   # заполнить /opt/auto-report/.env (шаблон — Auto_Report/.env.example).
#   # Права: владелец root, группа deploy, mode 640 — deploy может читать
#   # (docker compose --env-file требует чтения), но не писать.
#   sudo chown root:deploy /opt/auto-report/.env
#   sudo chmod 640 /opt/auto-report/.env

set -euo pipefail

# ─── Пути ─────────────────────────────────────────────────────────────
REPO_BACK=/opt/auto-report/Auto_Report
REPO_FRONT=/opt/auto-report/Auto_report_front
COMPOSE_DIR="$REPO_BACK"                      # docker-compose.yml в бэке
BACKUPS=/opt/auto-report/backups
ENV_FILE=/opt/auto-report/.env
# /tmp, а не /var/lock — последний по дефолту mode 755 root:root,
# deploy не сможет создать файл. /tmp mode 1777 — пишут все.
LOCK_FILE=/tmp/auto-report-deploy.lock

# ─── Аргумент ─────────────────────────────────────────────────────────
TARGET="${1:-all}"
case "$TARGET" in
    backend|frontend|all) ;;
    *) echo "[deploy] Использование: $0 {backend|frontend|all}"; exit 1 ;;
esac

echo "[deploy] $(date '+%F %T') target=$TARGET"

# ─── 1. Сериализация деплоев через flock ──────────────────────────────
exec 9>"$LOCK_FILE"
if ! flock -x -w 600 9; then
    echo "[deploy] Не удалось взять lock за 600s — выхожу"
    exit 1
fi
echo "[deploy] Lock acquired"

# ─── 2. Git fetch + reset на нужных репо ──────────────────────────────
pull_repo() {
    local dir=$1
    echo "[deploy] git fetch+reset prod в $dir"
    git -C "$dir" fetch --quiet origin prod
    git -C "$dir" reset --hard origin/prod
    git -C "$dir" log -1 --oneline
}

case "$TARGET" in
    backend|all)
        pull_repo "$REPO_BACK"
        ;;
esac
case "$TARGET" in
    frontend|all)
        pull_repo "$REPO_FRONT"
        ;;
esac

# ─── 3. Pre-deploy backup ──────────────────────────────────────────────
# Делаем ТОЛЬКО при backend/all. Фронт-деплой схему БД не трогает, а
# параллельный backend-деплой (наш частый кейс — оба GHA-workflow в одну
# минуту) может в этот момент гонять alembic upgrade head: тогда pg_dump
# зачитает pg_catalog в полёте DDL и упадёт "cache lookup failed for
# index NNNN". С set -euo pipefail это валит весь deploy.sh, и фронт-
# контейнер так и не пересобирается. См. memory feedback
# [[autoreport-deploy-vds-race]].
if [ "$TARGET" != "frontend" ]; then
    mkdir -p "$BACKUPS"
    TS=$(date +%Y%m%d-%H%M%S)
    BACKUP_FILE="$BACKUPS/pre-deploy-${TS}.sql.gz"

    if docker ps --format '{{.Names}}' | grep -q '^auto-report-postgres$'; then
        echo "[deploy] pg_dump → $BACKUP_FILE"
        DB_USER=$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | head -1 | cut -d= -f2)
        DB_NAME=$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | head -1 | cut -d= -f2)
        docker exec auto-report-postgres \
            pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"
        echo "[deploy] Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
    else
        echo "[deploy] postgres не запущен (первый деплой?) — пропуск pre-deploy backup"
    fi
else
    echo "[deploy] target=frontend — pg_dump пропускаем (БД не меняется)"
fi

# ─── 4. docker compose up ─────────────────────────────────────────────
cd "$COMPOSE_DIR"
case "$TARGET" in
    backend)
        echo "[deploy] docker compose up -d --build backend"
        docker compose up -d --build backend
        ;;
    frontend)
        echo "[deploy] docker compose up -d --build frontend"
        docker compose up -d --build frontend
        ;;
    all)
        echo "[deploy] docker compose up -d --build (все сервисы)"
        docker compose up -d --build
        ;;
esac

# ─── 5. Cleanup образов и старых бэкапов ──────────────────────────────
echo "[deploy] docker image prune -f"
docker image prune -f

# Pre-deploy бэкапы старше 14 дней — сносим. Ежедневные (§8) у них свой
# retention.
find "$BACKUPS" -name 'pre-deploy-*.sql.gz' -mtime +14 -delete 2>/dev/null || true

echo "[deploy] $(date '+%F %T') Готово"
