#!/usr/bin/env bash
# Auto_Report VDS — ежедневный бэкап.
#
# Запускается cron'ом из-под deploy-юзера в 03:00 по Europe/Moscow
# (см. /etc/cron.d/auto-report-backup).
#
# Что делает:
#   1. pg_dump БД через docker exec → /opt/auto-report/backups/db-TS.sql.gz
#   2. tar содержимого backend_media volume → media-TS.tar.gz
#   3. Ротация: всё в backups/ старше 14 дней — удалить.
#
# Локально не запускать (зависит от docker-volume layout и .env пути на VDS).
#
# ───── INITIAL SETUP CHEATSHEET (один раз на VDS под root) ─────
#   sudo cp /opt/auto-report/Auto_Report/scripts/backup_vds.sh \
#           /opt/auto-report/scripts/backup.sh
#   sudo chmod +x /opt/auto-report/scripts/backup.sh
#   sudo chown root:root /opt/auto-report/scripts/backup.sh
#
#   # cron-job:
#   sudo tee /etc/cron.d/auto-report-backup > /dev/null <<'EOF'
#   SHELL=/bin/bash
#   PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
#   0 3 * * * deploy /opt/auto-report/scripts/backup.sh >> /var/log/auto-report-backup.log 2>&1
#   EOF
#
#   # Чтобы log не разрастался — logrotate:
#   sudo tee /etc/logrotate.d/auto-report-backup > /dev/null <<'EOF'
#   /var/log/auto-report-backup.log {
#       weekly
#       rotate 4
#       compress
#       missingok
#       notifempty
#   }
#   EOF
#
#   # Тест: запустить руками и проверить, что файлы появились.
#   sudo -u deploy /opt/auto-report/scripts/backup.sh
#   ls -la /opt/auto-report/backups/

set -euo pipefail

BACKUPS=/opt/auto-report/backups
ENV_FILE=/opt/auto-report/.env

# Путь к данным named volume backend_media на хосте.
# Docker compose v2 берёт project name из basename папки compose
# (/opt/auto-report/Auto_Report → "Auto_Report" → lowercased "auto_report"
# С ПОДЧЁРКИВАНИЕМ, не дефисом), поэтому реальный путь:
MEDIA_DATA=/var/lib/docker/volumes/auto_report_backend_media/_data

mkdir -p "$BACKUPS"

TS=$(date +%Y%m%d-%H%M%S)
DB_FILE="$BACKUPS/db-${TS}.sql.gz"
MEDIA_FILE="$BACKUPS/media-${TS}.tar.gz"

# ─── 1. БД ────────────────────────────────────────────────────────────
if ! docker ps --format '{{.Names}}' | grep -q '^auto-report-postgres$'; then
    echo "[$TS] postgres не запущен — бэкап пропущен"
    exit 0
fi

DB_USER=$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | head -1 | cut -d= -f2)
DB_NAME=$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | head -1 | cut -d= -f2)

echo "[$TS] pg_dump → $DB_FILE"
docker exec auto-report-postgres \
    pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$DB_FILE"

# ─── 2. Media volume (вложения + шаблоны .docx) ───────────────────────
if [ -d "$MEDIA_DATA" ]; then
    echo "[$TS] tar media → $MEDIA_FILE"
    # sudo нужен — _data принадлежит root (docker volume).
    # backup.sh бежит под deploy через cron — но cron.d даёт deploy-юзеру
    # права через `0 3 * * * deploy ...`. Если deploy не может читать
    # /var/lib/docker/volumes/, можно либо chmod 755 на _data,
    # либо запускать backup.sh от root (изменить cron строку на `root`).
    tar -czf "$MEDIA_FILE" -C "$MEDIA_DATA" . 2>/dev/null \
        || echo "[$TS] WARN: не смог запаковать media (нет доступа к docker volumes?)"
else
    echo "[$TS] $MEDIA_DATA не существует — пропуск media-бэкапа"
fi

# ─── 3. Ротация: всё старше 14 дней удалить ───────────────────────────
find "$BACKUPS" -maxdepth 1 -name 'db-*.sql.gz'         -mtime +14 -delete 2>/dev/null || true
find "$BACKUPS" -maxdepth 1 -name 'media-*.tar.gz'      -mtime +14 -delete 2>/dev/null || true
find "$BACKUPS" -maxdepth 1 -name 'pre-deploy-*.sql.gz' -mtime +14 -delete 2>/dev/null || true

echo "[$TS] OK: db=$(du -h "$DB_FILE" 2>/dev/null | cut -f1 || echo -), media=$(du -h "$MEDIA_FILE" 2>/dev/null | cut -f1 || echo -)"
