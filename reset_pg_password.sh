#!/usr/bin/env bash
# reset_pg_password.sh
# Сбросить пароль локального PostgreSQL 16 (порт 5433) для роли postgres -> 'postgres'.
# Запускать из Git Bash ОТ ИМЕНИ АДМИНИСТРАТОРА:
#   правый клик на ярлык Git Bash -> "Запуск от имени администратора"
# После использования файл можно удалить.

set -e

PG_BIN="/c/Program Files/PostgreSQL/16/bin"
PG_DATA="/c/Program Files/PostgreSQL/16/data"
HBA="$PG_DATA/pg_hba.conf"
BAK="$HBA.bak.20260529"
NEW_PWD="postgres"

# 0. Проверка admin-прав (net session работает только у админа)
if ! net session >/dev/null 2>&1; then
    echo "ERROR: запустите Git Bash от имени администратора" >&2
    exit 1
fi

echo "[1/6] Бэкап pg_hba.conf -> $BAK"
[ -f "$BAK" ] || cp "$HBA" "$BAK"

echo "[2/6] Добавляю временную trust-запись для postgres@127.0.0.1"
TMP=$(mktemp)
printf 'host    all             postgres        127.0.0.1/32            trust\n' > "$TMP"
cat "$HBA" >> "$TMP"
cp "$TMP" "$HBA"
rm -f "$TMP"

echo "[3/6] Перезапуск службы postgresql-16"
net stop postgresql-16
net start postgresql-16
sleep 3

echo "[4/6] ALTER USER postgres PASSWORD '$NEW_PWD'"
"$PG_BIN/psql.exe" -h 127.0.0.1 -p 5433 -U postgres -d postgres \
    -c "ALTER USER postgres WITH PASSWORD '$NEW_PWD';"

echo "[5/6] Восстанавливаю исходный pg_hba.conf"
cp "$BAK" "$HBA"

echo "[6/6] Перезапуск службы postgresql-16"
net stop postgresql-16
net start postgresql-16
sleep 3

echo ""
echo "Готово. Пароль postgres = '$NEW_PWD'."
echo "Проверка:"
PGPASSWORD="$NEW_PWD" "$PG_BIN/psql.exe" -h 127.0.0.1 -p 5433 -U postgres -d postgres \
    -c "SELECT 'OK' AS status, current_user;"
