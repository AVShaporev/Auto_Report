# Auto_Report — деплой на Ubuntu 192.168.1.8

Развёртывание стека (PostgreSQL + FastAPI backend + Vue SPA + nginx) на одной локальной Ubuntu-машине, два окружения **stage** и **prod** на том же сервере, автодеплой через **self-hosted GitHub Actions runner** при пуше в одноимённые ветки.

Парный фронт-репозиторий: `Auto_report_front`. Этот файл покрывает обе части.

Альтернативный план для публичного VPS с Docker+Caddy+SOPS см. `DEPLOY_VPS.md`.

---

## 1. Целевая архитектура

```
                              192.168.1.8 (Ubuntu 22.04+)
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   nginx                                                              │
│     :80  →  prod   →  /opt/autoreport/prod/frontend/dist             │
│                  →  /api/  →  127.0.0.1:8000  (autoreport-api@prod)  │
│     :8080→  stage  →  /opt/autoreport/stage/frontend/dist            │
│                  →  /api/  →  127.0.0.1:8001  (autoreport-api@stage) │
│                                                                      │
│   systemd templated unit  autoreport-api@.service                    │
│     instance=prod   → ветка prod,  порт 8000, БД autoreport_prod    │
│     instance=stage  → ветка stage, порт 8001, БД autoreport_stage   │
│                                                                      │
│   PostgreSQL 16 :5432 (loopback)                                     │
│     БД: autoreport_prod, autoreport_stage                            │
│     роли: autoreport_prod, autoreport_stage (раздельные)             │
│                                                                      │
│   GitHub Actions self-hosted runner (systemd)                        │
│     юзер: github-runner, регистрируется в обоих репо                 │
│                                                                      │
│   Пользователи системы:                                              │
│     autoreport     — owner кода и venv, под ним работает uvicorn     │
│     github-runner  — owner runner-агента, выполняет workflow         │
│     www-data       — nginx                                           │
└──────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ GitHub Actions runner self-poll
                                  │
                              GitHub.com
```

Файловая структура на сервере:

```
/opt/autoreport/
  prod/
    backend/             ← Auto_Report, ветка prod
    frontend/dist/       ← залит из CI (npm run build)
  stage/
    backend/             ← Auto_Report, ветка stage
    frontend/dist/       ← залит из CI
  scripts/
    deploy-backend.sh    ← общий, принимает аргумент: prod | stage
    deploy-frontend.sh
    common.sh
  backups/

/etc/autoreport/
  prod.env               ← секреты prod  (chmod 640, root:autoreport)
  stage.env              ← секреты stage

/etc/systemd/system/
  autoreport-api@.service

/etc/nginx/sites-available/
  autoreport
```

Изоляция окружений:
- Разные ветки git, разные рабочие копии.
- Разные БД, разные роли PG (компрометация одной не открывает другую).
- Разные порты uvicorn.
- Разные nginx server-блоки (`listen 80` vs `listen 8080`).
- Один OS-юзер `autoreport` для обоих окружений (упрощает права; если нужна более жёсткая изоляция — заводим `autoreport_prod` и `autoreport_stage`).

---

## 2. Подготовка сервера

Все команды выполняются от пользователя с `sudo`.

### 2.1. Системные пакеты

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    build-essential curl git ufw \
    postgresql postgresql-contrib \
    python3.11 python3.11-venv python3-pip \
    nginx \
    rsync jq
```

Node.js 22 (для сборки фронта в CI, и на сервере опционально для smoke-проверок):

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt install -y nodejs
node -v
```

### 2.2. Пользователи системы

```bash
# системный юзер под бэк
sudo useradd --system --create-home --home-dir /home/autoreport \
    --shell /bin/bash autoreport

# юзер под self-hosted runner (его создаёт сам инсталлятор, но можем заранее)
sudo useradd --create-home --shell /bin/bash github-runner

# у runner-юзера должен быть доступ на запись в /opt/autoreport
sudo usermod -aG autoreport github-runner
```

Запретить логин по паролю:

```bash
sudo passwd -l autoreport
sudo passwd -l github-runner
```

### 2.3. Каталоги

```bash
sudo mkdir -p /opt/autoreport/{prod,stage,scripts,backups}
sudo mkdir -p /opt/autoreport/prod/{backend,frontend}
sudo mkdir -p /opt/autoreport/stage/{backend,frontend}
sudo mkdir -p /etc/autoreport

sudo chown -R github-runner:autoreport /opt/autoreport
sudo chmod -R 2775 /opt/autoreport    # setgid: новые файлы → группа autoreport

sudo chown root:autoreport /etc/autoreport
sudo chmod 750 /etc/autoreport
```

### 2.4. Firewall (ufw)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp     # SSH из локальной сети
sudo ufw allow 80/tcp     # nginx prod
sudo ufw allow 8080/tcp   # nginx stage
sudo ufw enable
sudo ufw status
```

Postgres (5432) и uvicorn-порты (8000/8001) наружу не открываем — слушают только loopback.

### 2.5. sudoers для runner

`/etc/sudoers.d/github-runner-autoreport` (создать через `sudo visudo -f`):

```
# Минимальные права github-runner для деплоя.
# Перезапуск API обоих окружений и reload nginx — без пароля.
github-runner ALL=(root) NOPASSWD: /bin/systemctl restart autoreport-api@prod
github-runner ALL=(root) NOPASSWD: /bin/systemctl restart autoreport-api@stage
github-runner ALL=(root) NOPASSWD: /bin/systemctl status  autoreport-api@prod
github-runner ALL=(root) NOPASSWD: /bin/systemctl status  autoreport-api@stage
github-runner ALL=(root) NOPASSWD: /bin/systemctl reload  nginx

# Запуск poetry/alembic от имени autoreport (без пароля)
github-runner ALL=(autoreport) NOPASSWD: /home/autoreport/.local/bin/poetry
```

Права файла должны быть 440 — `visudo` проверит автоматически.

---

## 3. PostgreSQL

### 3.1. Создание ролей и БД

Пароли сгенерировать заранее:

```bash
openssl rand -base64 32 | tr -d '=+/' | cut -c1-32   # для prod
openssl rand -base64 32 | tr -d '=+/' | cut -c1-32   # для stage
```

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE autoreport_prod  WITH LOGIN PASSWORD 'PROD_PASSWORD_HERE';
CREATE ROLE autoreport_stage WITH LOGIN PASSWORD 'STAGE_PASSWORD_HERE';

CREATE DATABASE autoreport_prod  OWNER autoreport_prod;
CREATE DATABASE autoreport_stage OWNER autoreport_stage;

GRANT ALL PRIVILEGES ON DATABASE autoreport_prod  TO autoreport_prod;
GRANT ALL PRIVILEGES ON DATABASE autoreport_stage TO autoreport_stage;
SQL
```

Эти же пароли пойдут в `/etc/autoreport/prod.env` и `stage.env` (§4).

### 3.2. Ограничить доступ к БД loopback'ом

`/etc/postgresql/16/main/postgresql.conf`:

```
listen_addresses = 'localhost'
```

`/etc/postgresql/16/main/pg_hba.conf` — оставить только:

```
local   all             postgres                                peer
local   all             all                                     scram-sha-256
host    autoreport_prod  autoreport_prod   127.0.0.1/32         scram-sha-256
host    autoreport_stage autoreport_stage  127.0.0.1/32         scram-sha-256
```

Применить:

```bash
sudo systemctl restart postgresql
```

Проверка:

```bash
PGPASSWORD='PROD_PASSWORD_HERE' psql -h 127.0.0.1 -U autoreport_prod  -d autoreport_prod  -c '\dt'
PGPASSWORD='STAGE_PASSWORD_HERE' psql -h 127.0.0.1 -U autoreport_stage -d autoreport_stage -c '\dt'
```

### 3.3. Ежедневный бэкап обеих БД

`/etc/cron.daily/autoreport-backup` (chmod 750, owner root):

```bash
#!/bin/bash
set -euo pipefail
TS=$(date +%Y-%m-%d_%H%M)
BACKUP_DIR=/opt/autoreport/backups

for ENV in prod stage; do
    ENV_FILE="/etc/autoreport/${ENV}.env"
    DB_NAME=$(grep ^DB_NAME "$ENV_FILE" | cut -d= -f2-)
    DB_USER=$(grep ^DB_USER "$ENV_FILE" | cut -d= -f2-)
    DB_PASSWORD=$(grep ^DB_PASSWORD "$ENV_FILE" | cut -d= -f2-)
    OUT="${BACKUP_DIR}/${DB_NAME}_${TS}.sql.gz"

    PGPASSWORD="$DB_PASSWORD" pg_dump -h 127.0.0.1 -U "$DB_USER" "$DB_NAME" | gzip > "$OUT"
done

find "$BACKUP_DIR" -name 'autoreport_*.sql.gz' -mtime +14 -delete
```

```bash
sudo chmod 750 /etc/cron.daily/autoreport-backup
sudo chown root:root /etc/cron.daily/autoreport-backup
```

---

## 4. Секреты — основной путь (systemd EnvironmentFile)

### 4.1. Файлы секретов

`/etc/autoreport/prod.env`:

```
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=autoreport_prod
DB_USER=autoreport_prod
DB_PASSWORD=<пароль из §3.1>
SECRET_KEY=<openssl rand -base64 64 | tr -d '\n='>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
MEDIA_ROOT=/opt/autoreport/prod/backend/media
UVICORN_PORT=8000
```

`/etc/autoreport/stage.env`:

```
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=autoreport_stage
DB_USER=autoreport_stage
DB_PASSWORD=<пароль из §3.1>
SECRET_KEY=<отдельный, не совпадает с prod>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
MEDIA_ROOT=/opt/autoreport/stage/backend/media
UVICORN_PORT=8001
```

Права:

```bash
sudo chown root:autoreport /etc/autoreport/prod.env /etc/autoreport/stage.env
sudo chmod 640 /etc/autoreport/prod.env /etc/autoreport/stage.env
```

Только `root` — запись, группа `autoreport` (и runner через групповое членство) — чтение. Никогда не в git.

### 4.2. Бэкап секретов

Копия — **вне сервера**:
- менеджер паролей (Bitwarden / 1Password) — рекомендую,
- зашифрованный архив на твоём ПК (`age -p` / `gpg -c`).

### 4.3. Альтернатива — SOPS + age в репо

Если хочешь версионировать секреты в репозитории — рабочий план в `DEPLOY_VPS.md` §3.4. Для одного локального сервера `EnvironmentFile` достаточно и проще.

---

## 5. Backend — установка и systemd unit

### 5.1. Poetry для пользователя autoreport

```bash
sudo -u autoreport -H bash -lc '
    curl -sSL https://install.python-poetry.org | python3 -
    echo "export PATH=\$HOME/.local/bin:\$PATH" >> ~/.profile
'
```

### 5.2. Первый клон (вручную, для каждого окружения)

Под `github-runner`:

```bash
sudo -u github-runner bash -lc '
    cd /opt/autoreport/prod
    git clone https://github.com/<owner>/Auto_Report.git backend
    cd backend && git checkout prod

    cd /opt/autoreport/stage
    git clone https://github.com/<owner>/Auto_Report.git backend
    cd backend && git checkout stage
'
```

Установить зависимости и накатить миграции под `autoreport` (для каждого окружения):

```bash
# PROD
sudo -u autoreport -H bash -lc '
    cd /opt/autoreport/prod/backend
    ~/.local/bin/poetry install --only main --no-root
    set -a; . /etc/autoreport/prod.env; set +a
    ~/.local/bin/poetry run alembic upgrade head
'

# STAGE — то же самое, заменяя prod на stage
```

Каталоги для логов и медиа:

```bash
sudo -u autoreport mkdir -p /opt/autoreport/prod/backend/{logs,media}
sudo -u autoreport mkdir -p /opt/autoreport/stage/backend/{logs,media}
```

### 5.3. systemd templated unit

`/etc/systemd/system/autoreport-api@.service`:

```ini
[Unit]
Description=Auto_Report FastAPI backend (%i)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=autoreport
Group=autoreport
WorkingDirectory=/opt/autoreport/%i/backend
EnvironmentFile=/etc/autoreport/%i.env
ExecStart=/home/autoreport/.local/bin/poetry run uvicorn main:app \
    --host 127.0.0.1 --port ${UVICORN_PORT} --workers 2
Restart=on-failure
RestartSec=5

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/opt/autoreport/%i/backend/logs /opt/autoreport/%i/backend/media

[Install]
WantedBy=multi-user.target
```

`%i` подставит instance: `autoreport-api@prod` → `prod`. Один файл — оба окружения.

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now autoreport-api@prod
sudo systemctl enable --now autoreport-api@stage
sudo systemctl status autoreport-api@prod
sudo systemctl status autoreport-api@stage
curl -s http://127.0.0.1:8000/docs | head -n 3
curl -s http://127.0.0.1:8001/docs | head -n 3
```

Логи:

```bash
sudo journalctl -u autoreport-api@prod  -f
sudo journalctl -u autoreport-api@stage -f
tail -f /opt/autoreport/prod/backend/logs/app.log
tail -f /opt/autoreport/stage/backend/logs/app.log
```

---

## 6. Frontend

Сборку фронта делает CI (см. §8.5), на сервер заливается готовый `dist/`. Первый раз можно собрать на сервере — чтобы было что отдавать через nginx до первого workflow-run:

```bash
sudo -u github-runner bash -lc '
    for ENV in prod stage; do
        cd /opt/autoreport/$ENV
        git clone https://github.com/<owner>/Auto_report_front.git frontend
        cd frontend && git checkout $ENV
        npm ci
        cat > .env <<EOF
VITE_API_BASE_URL=/api
EOF
        npm run build
    done
'
```

`dist/` остаётся в `/opt/autoreport/<env>/frontend/dist/` — оттуда nginx и отдаёт статику.

---

## 7. Nginx

`/etc/nginx/sites-available/autoreport`:

```nginx
# ============= PROD =============
server {
    listen 80 default_server;
    server_name 192.168.1.8 _;

    access_log /var/log/nginx/autoreport-prod.access.log;
    error_log  /var/log/nginx/autoreport-prod.error.log warn;

    client_max_body_size 50M;
    root /opt/autoreport/prod/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
    location ~* \.(?:js|css|woff2?|svg|ico|png|jpg|jpeg)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
    location /media/ {
        alias /opt/autoreport/prod/backend/media/;
        expires 1d;
    }
}

# ============= STAGE =============
server {
    listen 8080;
    server_name 192.168.1.8 _;

    access_log /var/log/nginx/autoreport-stage.access.log;
    error_log  /var/log/nginx/autoreport-stage.error.log warn;

    client_max_body_size 50M;
    root /opt/autoreport/stage/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
    location ~* \.(?:js|css|woff2?|svg|ico|png|jpg|jpeg)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
    location /media/ {
        alias /opt/autoreport/stage/backend/media/;
        expires 1d;
    }
}
```

Активация:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/autoreport /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Доступ:
- prod  — `http://192.168.1.8/`
- stage — `http://192.168.1.8:8080/`

---

## 8. Autodeploy — Self-hosted GitHub Actions runner

Push в ветку `prod` или `stage` → GitHub отдаёт job runner'у на 192.168.1.8 → runner запускает `scripts/deploy-*.sh <env>`.

Runner-агент сам инициирует исходящие соединения к GitHub (HTTPS) — белый IP сервера не нужен. Это критическое отличие от схемы appleboy/ssh-action в `DEPLOY_VPS.md`.

### 8.1. Установка runner-агента

Один агент будет обслуживать оба репо (бэк и фронт). Это самый простой вариант; если хочется изоляции — поставить два с разными `--name`.

```bash
sudo mkdir -p /opt/actions-runner
sudo chown github-runner:github-runner /opt/actions-runner
sudo -u github-runner -H bash <<'BASH'
cd /opt/actions-runner
curl -o actions-runner-linux-x64.tar.gz -L \
    https://github.com/actions/runner/releases/download/v2.319.1/actions-runner-linux-x64-2.319.1.tar.gz
tar xzf actions-runner-linux-x64.tar.gz
BASH
```

### 8.2. Регистрация в обоих репозиториях

В GitHub: **Settings → Actions → Runners → New self-hosted runner** в каждом из двух репо (`Auto_Report` и `Auto_report_front`). GitHub выдаст одноразовый token. Команды для каждого репо:

```bash
sudo -u github-runner -H bash -lc '
    cd /opt/actions-runner
    ./config.sh \
        --url https://github.com/<owner>/Auto_Report \
        --token <TOKEN_FROM_GITHUB> \
        --name "autoreport-srv" \
        --labels "self-hosted,autoreport,linux" \
        --work _work \
        --unattended
'
```

После настройки одного репо повторить для второго репо в том же runner-агенте — но **runner-агент привязывается к одному репо за раз** (если не используется organization-level runner). Варианты:

1. **Два runner-агента в одном каталоге** — поставить второй в `/opt/actions-runner-frontend`, повторить установку и регистрацию, использовать labels для маршрутизации.
2. **Organization-level runner** — если репо переехать в organization, один runner может обслуживать все репо организации. Сейчас, вероятно, оба репо в личном аккаунте — этот вариант недоступен.

Рекомендую **два каталога**:

```bash
sudo mkdir -p /opt/actions-runner-backend /opt/actions-runner-frontend
sudo chown github-runner:github-runner /opt/actions-runner-{backend,frontend}
# Повторить установку и config.sh в каждом, указывая нужный --url репозитория.
```

### 8.3. systemd unit для runner

GitHub предлагает свой инсталлятор (`svc.sh install`), но он создаёт root-овый юнит. Свой юнит чище.

`/etc/systemd/system/gh-runner@.service`:

```ini
[Unit]
Description=GitHub Actions self-hosted runner (%i)
After=network.target

[Service]
Type=simple
User=github-runner
Group=github-runner
WorkingDirectory=/opt/actions-runner-%i
ExecStart=/opt/actions-runner-%i/run.sh
Restart=on-failure
RestartSec=10
KillMode=process

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gh-runner@backend
sudo systemctl enable --now gh-runner@frontend
sudo systemctl status gh-runner@backend
sudo systemctl status gh-runner@frontend
```

В GitHub UI оба runner'а должны появиться в статусе **Idle**.

### 8.4. Скрипты деплоя на сервере

`/opt/autoreport/scripts/common.sh`:

```bash
#!/bin/bash
# Общие функции для deploy-*.sh
set -euo pipefail

require_env() {
    case "$1" in
        prod|stage) ;;
        *) echo "ENV must be 'prod' or 'stage', got: $1" >&2; exit 2;;
    esac
}

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
```

`/opt/autoreport/scripts/deploy-backend.sh`:

```bash
#!/bin/bash
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
log "  $OLD → $NEW"

# зависимости
sudo -u autoreport -H /home/autoreport/.local/bin/poetry \
    --directory "$REPO" install --only main --no-root --sync

# миграции
sudo -u autoreport -H bash -lc "
    cd '$REPO'
    set -a; . /etc/autoreport/${ENV}.env; set +a
    /home/autoreport/.local/bin/poetry run alembic upgrade head
"

# рестарт
sudo /bin/systemctl restart "autoreport-api@${ENV}"
sleep 2
sudo /bin/systemctl status "autoreport-api@${ENV}" --no-pager

log "Backend deploy: OK"
```

`/opt/autoreport/scripts/deploy-frontend.sh`:

```bash
#!/bin/bash
set -euo pipefail
source /opt/autoreport/scripts/common.sh

ENV=${1:?usage: deploy-frontend.sh <prod|stage>}
require_env "$ENV"

REPO=/opt/autoreport/$ENV/frontend
BRANCH=$ENV

log "Frontend deploy: env=$ENV branch=$BRANCH"

# обновим репо с кодом (CLAUDE.md и т.п.); сам dist обновляется
# rsync'ом из workflow ДО запуска этого скрипта (см. §8.5)
cd "$REPO"
git fetch --quiet origin "$BRANCH"
git reset --hard "origin/$BRANCH"

# smoke: dist должен существовать и быть не пустым
test -s "$REPO/dist/index.html" || { log "dist/index.html missing"; exit 1; }

# nginx сам подцепит обновлённую статику; reload не нужен
log "Frontend deploy: OK at $(git rev-parse --short HEAD)"
```

Установка:

```bash
sudo chown github-runner:autoreport /opt/autoreport/scripts/*.sh
sudo chmod 750 /opt/autoreport/scripts/*.sh
```

### 8.5. Workflow для бэка

В репо **Auto_Report**, файл `.github/workflows/deploy.yml`:

```yaml
name: Deploy backend

on:
  push:
    branches: [prod, stage]
  workflow_dispatch:
    inputs:
      env:
        description: 'Environment'
        required: true
        type: choice
        options: [prod, stage]

concurrency:
  group: deploy-backend-${{ github.ref_name }}
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: [self-hosted, autoreport, linux]
    steps:
      - name: Resolve environment
        id: env
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
              echo "name=${{ inputs.env }}" >> $GITHUB_OUTPUT
          else
              echo "name=${{ github.ref_name }}" >> $GITHUB_OUTPUT
          fi

      - name: Deploy
        run: /opt/autoreport/scripts/deploy-backend.sh ${{ steps.env.outputs.name }}

      - name: Smoke test
        run: |
          if [ "${{ steps.env.outputs.name }}" = "prod" ]; then PORT=8000; else PORT=8001; fi
          for i in 1 2 3 4 5; do
              curl -fsS "http://127.0.0.1:${PORT}/docs" > /dev/null && exit 0
              sleep 2
          done
          echo "Smoke failed"; exit 1
```

`runs-on` лейблы должны совпадать с теми, что были заданы при `config.sh --labels ...` (§8.2).

### 8.6. Workflow для фронта

В репо **Auto_report_front**, файл `.github/workflows/deploy.yml`:

```yaml
name: Deploy frontend

on:
  push:
    branches: [prod, stage]
  workflow_dispatch:
    inputs:
      env:
        description: 'Environment'
        required: true
        type: choice
        options: [prod, stage]

concurrency:
  group: deploy-frontend-${{ github.ref_name }}
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: [self-hosted, autoreport, linux]
    steps:
      - uses: actions/checkout@v4

      - name: Resolve environment
        id: env
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
              echo "name=${{ inputs.env }}" >> $GITHUB_OUTPUT
          else
              echo "name=${{ github.ref_name }}" >> $GITHUB_OUTPUT
          fi

      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'

      - run: npm ci

      - name: Build
        env:
          VITE_API_BASE_URL: /api
        run: npm run build

      - name: Sync dist
        run: |
          ENV=${{ steps.env.outputs.name }}
          rsync -a --delete dist/ /opt/autoreport/$ENV/frontend/dist/

      - name: Post-deploy
        run: /opt/autoreport/scripts/deploy-frontend.sh ${{ steps.env.outputs.name }}
```

Поскольку runner крутится прямо на 192.168.1.8 — никакого SSH/rsync-over-network не нужно, `rsync` локальный.

### 8.7. Откат

```bash
sudo -u github-runner bash -lc '
    cd /opt/autoreport/prod/backend
    git reset --hard <prev-sha>
'
sudo systemctl restart autoreport-api@prod
```

Или через `git revert` коммита и push в `prod` — workflow прокатит откат как обычный деплой. **Миграции должны быть совместимы с downgrade** — иначе пиши новую миграцию вперёд.

---

## 9. Логи и наблюдаемость

| Что | Где |
| --- | --- |
| API stdout/stderr | `journalctl -u autoreport-api@{prod,stage} -f` |
| API файловые логи | `/opt/autoreport/{prod,stage}/backend/logs/app.log` |
| Nginx | `/var/log/nginx/autoreport-{prod,stage}.{access,error}.log` |
| Postgres | `/var/log/postgresql/postgresql-16-main.log` |
| Деплои | вкладка Actions в каждом репо |
| Runner-агент | `journalctl -u gh-runner@{backend,frontend} -f` |

Бэк уже использует `loguru` с `enqueue=True`/`delay=True`/`catch=True` (`main.py:82`) — безопасно для ротации логов.

---

## 10. Гигиена и ротация

- **SECRET_KEY** — раз в 6 месяцев, отдельно для prod и stage.
- **DB_PASSWORD** — раз в 3-6 месяцев:
  ```sql
  ALTER USER autoreport_prod  WITH PASSWORD '<новый>';
  ALTER USER autoreport_stage WITH PASSWORD '<новый>';
  ```
  потом обновить `/etc/autoreport/{prod,stage}.env` и `sudo systemctl restart autoreport-api@{prod,stage}`.
- **Runner registration token** GitHub ротирует автоматически (сам токен — короткоживущий, агент использует постоянный credential, выданный при `config.sh`). При компрометации сервера — пересоздать агенты (`./config.sh remove --token <new>`).
- **Бэкапы БД** — раз в неделю проверять восстановление:
  ```bash
  gunzip -c /opt/autoreport/backups/autoreport_prod_<TS>.sql.gz | head -50
  ```

---

## 11. Чек-лист первого ручного деплоя

1. `[ ]` Сервер обновлён, пакеты установлены (§2.1).
2. `[ ]` Созданы пользователи `autoreport`, `github-runner` (§2.2).
3. `[ ]` Каталоги `/opt/autoreport/{prod,stage,scripts,backups}` и `/etc/autoreport/` созданы с нужными правами (§2.3).
4. `[ ]` Настроен `ufw`: 22/80/8080 (§2.4).
5. `[ ]` `sudoers.d/github-runner-autoreport` создан (§2.5).
6. `[ ]` PostgreSQL установлен, две роли + две БД созданы, `pg_hba` ограничен (§3.1-3.2).
7. `[ ]` `/etc/autoreport/{prod,stage}.env` созданы с правами 640, root:autoreport (§4.1).
8. `[ ]` Poetry установлен для autoreport (§5.1).
9. `[ ]` Бэк склонирован в `prod/` и `stage/`, зависимости поставлены, миграции прогнаны (§5.2).
10. `[ ]` `autoreport-api@.service` создан, оба instance стартуют (§5.3).
11. `[ ]` Фронт собран, dist/ есть в обоих окружениях (§6).
12. `[ ]` Nginx-конфиг работает: `http://192.168.1.8/` и `http://192.168.1.8:8080/` отвечают (§7).
13. `[ ]` Deploy-скрипты лежат, права 750 (§8.4).
14. `[ ]` Runner-агенты `backend` и `frontend` зарегистрированы в обоих репо, видны в GitHub UI как Idle (§8.1-8.2).
15. `[ ]` `gh-runner@.service` стартует оба instance (§8.3).
16. `[ ]` Workflow-файлы закоммичены в обоих репо (§8.5-8.6).
17. `[ ]` Тестовый push в `stage` бэка → autoreport-api@stage перезапустился, smoke прошёл.
18. `[ ]` Тестовый push в `stage` фронта → dist обновился, открыть `http://192.168.1.8:8080/` — изменения видны.
19. `[ ]` То же для `prod`.
20. `[ ]` Cron-бэкап БД работает (§3.3).

---

## 12. Troubleshooting

| Симптом | Куда смотреть |
| --- | --- |
| 502 Bad Gateway от nginx | `journalctl -u autoreport-api@<env> -n 50` — uvicorn упал? |
| `password authentication failed for user "autoreport_*"` | `grep DB_PASSWORD /etc/autoreport/<env>.env` — пароль совпадает с PG-ролью? |
| `peer authentication failed` | проверь `pg_hba.conf` — для `127.0.0.1` должен быть `scram-sha-256`, не `peer` |
| `Permission denied` в логах uvicorn | `chown -R autoreport:autoreport /opt/autoreport/<env>/backend/{logs,media}` |
| Workflow не запускается | в GitHub Actions → должен быть видим runner; `journalctl -u gh-runner@<name>` |
| Runner offline после ребута | `systemctl is-enabled gh-runner@<name>` — должно быть enabled |
| `sudo: systemctl: command not found` в скрипте | путь — `/bin/systemctl`, проверь sudoers (§2.5) |
| Миграция падает | `poetry run alembic current` / `history`; правь ручную downgrade-логику |
| `git pull` конфликтует | кто-то правил код прямо на сервере — нельзя. `git reset --hard origin/<env>` чинит |

---

## 13. Будущие улучшения

- **HTTPS**: настроить `caddy` рядом с nginx (отдельные порты 443) или поставить `certbot --nginx`, если будет DNS-имя.
- **Мониторинг**: Uptime Kuma на том же сервере (smoke prod/stage каждые 60s).
- **Алёрты**: Telegram-action после успешного/неудачного деплоя.
- **Изоляция миграций**: отдельный systemd one-shot `autoreport-migrate@.service` через `ExecStartPre=`.
- **Изоляция OS-юзеров**: разделить `autoreport` на `autoreport_prod` и `autoreport_stage` (если stage будет использоваться для PR-превью с непроверенным кодом).
- **Organization-level runner**: если репо переедут в organization, один runner-агент сможет обслуживать оба репо (упростит §8.2).

---

## Связанные документы

- `CLAUDE.md` — структура проекта, конвенции.
- `..\Auto_report_front\CLAUDE.md` — структура фронта.
- `DEPLOY_VPS.md` — альтернативный план для публичного VPS (Docker + Caddy + SOPS).
- Открытый пункт #14 — смена пароля БД на текущем проде `192.168.1.8` (`ALTER USER autoreport WITH PASSWORD '…'` + обновить `.env`). По этой схеме закроется автоматически при первой настройке prod-окружения: пароль для роли `autoreport_prod` ставится новый, ни старая роль `autoreport`, ни её слабый пароль `autoreport` больше нигде не используются. Старую роль после переезда удалить (`DROP ROLE autoreport;`).
