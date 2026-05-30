# reset_pg_password.ps1
# Одноразовый скрипт: сбросить пароль локального PostgreSQL 16 (на порту 5433)
# для роли `postgres` на 'postgres'. Запускать ОТ ИМЕНИ АДМИНИСТРАТОРА.
# После использования файл можно удалить.

$ErrorActionPreference = "Stop"

$pgBin  = "C:\Program Files\PostgreSQL\16\bin"
$pgData = "C:\Program Files\PostgreSQL\16\data"
$hba    = Join-Path $pgData "pg_hba.conf"
$bak    = "$hba.bak.20260529"
$newPwd = "postgres"

# 0. Проверка админ-прав
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Запустите PowerShell от имени администратора"
    exit 1
}

Write-Host "[1/6] Бэкап pg_hba.conf -> $bak" -ForegroundColor Cyan
if (-not (Test-Path $bak)) { Copy-Item $hba $bak -Force }

Write-Host "[2/6] Добавляю временную trust-запись для postgres@127.0.0.1" -ForegroundColor Cyan
$orig = Get-Content $hba -Raw
$tmp  = "host    all             postgres        127.0.0.1/32            trust`r`n" + $orig
Set-Content -Path $hba -Value $tmp -Encoding ASCII -NoNewline

Write-Host "[3/6] Restart-Service postgresql-16" -ForegroundColor Cyan
Restart-Service postgresql-16

Start-Sleep -Seconds 3

Write-Host "[4/6] ALTER USER postgres PASSWORD '$newPwd'" -ForegroundColor Cyan
& "$pgBin\psql.exe" -h 127.0.0.1 -p 5433 -U postgres -d postgres -c "ALTER USER postgres WITH PASSWORD '$newPwd';"

Write-Host "[5/6] Восстанавливаю исходный pg_hba.conf" -ForegroundColor Cyan
Copy-Item $bak $hba -Force

Write-Host "[6/6] Restart-Service postgresql-16" -ForegroundColor Cyan
Restart-Service postgresql-16

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Готово. Пароль postgres = '$newPwd'." -ForegroundColor Green
Write-Host "Проверка:" -ForegroundColor Yellow
$env:PGPASSWORD = $newPwd
& "$pgBin\psql.exe" -h 127.0.0.1 -p 5433 -U postgres -d postgres -c "SELECT 'OK' AS status, current_user;"
