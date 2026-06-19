#!/bin/bash
# install-env-file.sh — материализовать /etc/autoreport/<env>.env из
# временного файла, который написал decrypt-env.sh.
#
# Зачем отдельный скрипт, а не inline в sudoers'е:
# - sudoers сравнивает argv ПОБАЙТНО, любая опечатка в правиле = отвал.
#   Один helper-скрипт с фиксированными аргументами проще аудитить и поддерживать.
# - Скрипт сам валидирует ENV (только prod|stage), чтобы даже если sudoers-
#   правило когда-нибудь расширят — не получилось «install-env-file ../../etc/shadow».
#
# Запускается ТОЛЬКО через sudo от github-runner:
#   sudo /opt/autoreport/scripts/install-env-file.sh prod
#   sudo /opt/autoreport/scripts/install-env-file.sh stage
#
# Источник `/tmp/auto-report-deploy.192-<env>.env` — пишет `scripts/decrypt-env.sh`
# (он же выставит mode 0600). install переносит как root:autoreport 0640 — чтобы
# systemd unit autoreport-api@<env> (запускается под autoreport) прочитал.
#
# Этот скрипт лежит на сервере в /opt/autoreport/scripts/install-env-file.sh.
# В репо — копия в deploy/192-server-scripts/ для документации и истории.

set -euo pipefail

ENV=${1:?usage: install-env-file.sh <prod|stage>}

case "$ENV" in
    prod|stage) ;;
    *)
        echo "ENV must be prod or stage, got: $ENV" >&2
        exit 1
        ;;
esac

SRC="/tmp/auto-report-deploy.192-${ENV}.env"
DST="/etc/autoreport/${ENV}.env"

if [[ ! -f "$SRC" ]]; then
    echo "[install-env-file] Source $SRC not found — decrypt-env.sh must run first" >&2
    exit 1
fi

# install(1):
#   -m 640        — права для systemd EnvironmentFile (autoreport читает как член группы)
#   -o root       — собственник: root, deploy-юзер не должен мочь править после материализации
#   -g autoreport — группа: чтобы юзер autoreport (uvicorn) мог прочитать
#   -T            — target — это файл, а не директория (иначе если /etc/autoreport/<env>.env
#                   когда-нибудь не существует — install создаст под этим именем директорию)
install -m 640 -o root -g autoreport -T "$SRC" "$DST"

echo "[install-env-file] $SRC -> $DST (root:autoreport 640)"
