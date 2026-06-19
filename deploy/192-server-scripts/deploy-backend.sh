#!/bin/bash
# deploy-backend.sh — деплой бэкенда на 192.168.1.8.
#
# Лежит в /opt/autoreport/scripts/deploy-backend.sh.
# В репо — копия в deploy/192-server-scripts/ для истории.
#
# Вызывается из .github/workflows/deploy.yml на self-hosted runner'е
# (actions.runner.AVShaporev-Auto_Report.autoreport-srv-backend.service,
#  user=github-runner).
#
# Изменения относительно прежней версии (Этап 0.8 SOPS+age, 2026-06-19):
#   1. После git reset --hard добавлен блок «SOPS»: расшифровка
#      deploy/secrets/192-<env>.env.sops → /tmp/auto-report-deploy.192-<env>.env
#      → install как /etc/autoreport/<env>.env через helper install-env-file.sh
#      (sudo, NOPASSWD-правило в /etc/sudoers.d/github-runner-sops).
#   2. trap гарантирует удаление /tmp-файла при любом выходе.
#   3. Поскольку git pull первым делом обновляет scripts/decrypt-env.sh —
#      достаточно держать в репо актуальную версию скрипта, на сервере её
#      руками поддерживать не надо. То же касается install-env-file.sh
#      в идеале, но он в /opt/autoreport/scripts/ умышленно (фиксированный
#      путь для sudoers-правила, не зависит от env).

set -euo pipefail
source /opt/autoreport/scripts/common.sh

ENV=${1:?usage: deploy-backend.sh <prod|stage>}
require_env "$ENV"

REPO=/opt/autoreport/$ENV/backend
BRANCH=$ENV

log "Backend deploy: env=$ENV branch=$BRANCH"
cd "$REPO"

git fetch --quiet origin "$BRANCH"
OLD=$(git rev-parse HEAD)
git reset --hard "origin/$BRANCH"
NEW=$(git rev-parse HEAD)
log "  $OLD -> $NEW"

# === SOPS: материализовать /etc/autoreport/${ENV}.env из git ===
# decrypt-env.sh пишет /tmp/auto-report-deploy.192-<env>.env (mode 0600),
# install-env-file.sh переносит как /etc/autoreport/<env>.env (root:autoreport 640),
# который читает и systemd unit, и блок миграций ниже.
# trap гарантирует удаление /tmp-файла при ЛЮБОМ выходе.
log "[sops] decrypt + install /etc/autoreport/${ENV}.env"
TMP_ENV=$("$REPO/scripts/decrypt-env.sh" "192-${ENV}")
trap 'rm -f "$TMP_ENV"' EXIT
sudo /opt/autoreport/scripts/install-env-file.sh "$ENV"

# зависимости (poetry перепоставит venv, только если изменился lock)
sudo -u autoreport -H /home/autoreport/.local/bin/poetry \
    --directory "$REPO" install --only main --no-root --sync

# миграции (читают только что обновлённый /etc/autoreport/${ENV}.env)
sudo -u autoreport -H bash -lc "
    cd '$REPO'
    set -a; . /etc/autoreport/${ENV}.env; set +a
    /home/autoreport/.local/bin/poetry run alembic upgrade head
"

# рестарт
sudo /usr/bin/systemctl restart "autoreport-api@${ENV}"
sleep 2
sudo /usr/bin/systemctl status "autoreport-api@${ENV}" --no-pager | head -10

log "Backend deploy: OK"
