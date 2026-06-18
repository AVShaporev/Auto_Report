#!/usr/bin/env bash
# scripts/decrypt-env.sh — расшифровать SOPS-зашифрованный .env во временный файл.
#
# Зачем нужен отдельный скрипт, а не inline-вызов sops в deploy_vds.sh:
# - Тот же поток нужен в трёх местах: ручная отладка локально, deploy_vds.sh
#   на сервере, GitHub Actions. Дублирование рано или поздно разойдётся.
# - Печатать путь к /tmp-файлу позволяет caller'у захватить его в переменную
#   и потом аккуратно удалить через trap — даже если деплой упал посередине.
# - Корректные права (0600) ставим один раз тут, чтобы не забыть в трёх местах.
#
# Использование:
#   /path/to/decrypt-env.sh <env-name>
#   # печатает в stdout путь к /tmp/auto-report-deploy.<env-name>.env
#   # exit code != 0 — что-то не так (см. сообщения в stderr).
#
# Пример из deploy_vds.sh:
#   ENV_FILE=$(scripts/decrypt-env.sh vds-prod)
#   trap 'rm -f "$ENV_FILE"' EXIT
#   docker compose --env-file "$ENV_FILE" up -d
#
# Откуда берётся приватный ключ:
# - Если SOPS_AGE_KEY_FILE уже выставлен — sops использует его (явная воля).
# - Иначе если есть /etc/sops/age/keys.txt — выставляем сюда (типовое
#   серверное размещение, root:deploy 640).
# - Иначе sops сам найдёт ключ в дефолтных местах: ~/.config/sops/age/keys.txt
#   на Linux/Mac, %APPDATA%\sops\age\keys.txt на Windows. Для локальной
#   разработки этого достаточно.
# - Если ключа нигде нет — sops упадёт с «no identity matched», и мы тоже
#   завершимся ненулевым кодом.

set -euo pipefail

# === 1. Аргументы ===
# Один позиционный — имя env'а. Никакой автодетекции, потому что промахнуться
# одной буквой при ротации SECRET_KEY и расшифровать не тот файл — слишком
# дорогая ошибка. Явное лучше неявного.
if [[ $# -ne 1 ]]; then
  cat >&2 <<EOF
Использование: $0 <env-name>

Примеры env-name:
  vds-prod    -> deploy/secrets/vds-prod.env.sops
  192-stage   -> deploy/secrets/192-stage.env.sops
  192-prod    -> deploy/secrets/192-prod.env.sops
EOF
  exit 1
fi

ENV_NAME="$1"

# Простая валидация имени — только латиница/цифры/тире/подчёркивание. Защита
# от случайного "../../etc/shadow" в аргументе.
if [[ ! "$ENV_NAME" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "ОШИБКА: env-name '$ENV_NAME' содержит недопустимые символы." >&2
  echo "Разрешены: A-Z a-z 0-9 - _" >&2
  exit 1
fi

# === 2. Пути ===
# Скрипт лежит в scripts/, корень проекта — на уровень выше. readlink -f нужен
# на случай симлинков (часто бывает на CI / на сервере под deploy-юзером).
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOPS_FILE="$PROJECT_ROOT/deploy/secrets/$ENV_NAME.env.sops"

if [[ ! -f "$SOPS_FILE" ]]; then
  echo "ОШИБКА: $SOPS_FILE не найден." >&2
  echo "Список доступных env-ов:" >&2
  ls -1 "$PROJECT_ROOT/deploy/secrets/" 2>/dev/null \
    | grep -E '\.env\.sops$' \
    | sed -E 's/\.env\.sops$//' \
    | sed 's/^/  /' >&2 || echo "  (deploy/secrets/ пустая или отсутствует)" >&2
  exit 1
fi

# === 3. Поиск приватного age-ключа ===
# По возрастанию приоритета — явная переменная окружения побеждает.
if [[ -z "${SOPS_AGE_KEY_FILE:-}" ]]; then
  if [[ -r "/etc/sops/age/keys.txt" ]]; then
    # На VDS и на 192.168.1.8 кладём ключ сюда (root:deploy 640). Никаких
    # ~/.config/sops у deploy-юзера нет — он непривилегированный, в GHA-
    # раннер тоже без $HOME-настроек.
    export SOPS_AGE_KEY_FILE="/etc/sops/age/keys.txt"
  fi
  # Если /etc/sops/age/keys.txt нет — оставляем SOPS_AGE_KEY_FILE пустым,
  # sops сам поищет ключ в дефолтных местах (~/.config/sops/age/keys.txt
  # на Linux, %APPDATA%\sops\age\keys.txt на Windows). Для разработчика
  # на ноутбуке этого хватает.
fi

# === 4. Куда расшифровываем ===
# Per-env имя файла, чтобы два параллельных запуска (например, stage и prod
# деплои на 192.168.1.8 одновременно) не затирали друг другу содержимое.
# /tmp специально — большинство дистрибутивов чистят его при ребуте,
# и tmpfs обычно. Не пишем в /var/tmp (там переживает ребут — лишний риск).
OUT="/tmp/auto-report-deploy.$ENV_NAME.env"

# Жёсткий umask на время записи — даже если кто-то поправит sops и он
# создаст файл с дефолтными правами (0644), у нас не утечёт content.
# chmod после — на всякий случай (некоторые fs не уважают umask).
umask 077
sops --input-type dotenv --output-type dotenv -d "$SOPS_FILE" > "$OUT"
chmod 600 "$OUT"

# Печатаем путь в stdout — единственная строка, которую видит caller.
# Все ошибки выше шли в stderr, чтобы не засорять capture.
echo "$OUT"
