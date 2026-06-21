# План деплоя Auto_Report (FastAPI + Vue) на VPS

> Цель: развернуть на одном VPS три Docker-контейнера — PostgreSQL, FastAPI-бэкенд, Vue-фронтенд — и автоматически пересобирать стек при коммитах в `main` бэка и/или фронта.

Парный фронт: `..\..\Auto_report_front\auto_report_front` (отдельный git-репозиторий).

Этот документ — **план**, а не реализация. Сами Dockerfile'ы, `docker-compose.yml`, конфиги nginx и GitHub Actions создаются по шагам ниже; пока их нет в репо.

---

## 1. Архитектура

```
                       ┌──────────────────────────────────────────┐
   Internet :443       │                  VPS                     │
   ──────────►  Caddy (host) ──┬─► :80 frontend-nginx  (SPA + /api proxy)
                       │       │
                       │       └─► /api/* ──► backend :8000 (uvicorn/FastAPI)
                       │                              │
                       │                              ▼
                       │                        postgres :5432
                       │
                       └──────────────────────────────────────────┘
                                       docker network: ar_net
```

**Три контейнера в docker-compose:**

| Сервис      | Образ                       | Назначение                                                   |
|-------------|-----------------------------|--------------------------------------------------------------|
| `postgres`  | `postgres:16-alpine`        | БД, данные в named volume `pg_data`                          |
| `backend`   | свой build (Dockerfile)     | FastAPI + uvicorn, alembic migrations на старте              |
| `frontend`  | свой build (multi-stage)    | nginx, отдаёт SPA-сборку и проксирует `/api/*` на `backend`  |

**TLS / HTTPS:** Caddy на ХОСТЕ (вне docker) терминирует TLS, проксирует `:443 → frontend-nginx :80`. Caddy сам получает и обновляет Let's Encrypt. Это сохраняет ровно три docker-контейнера и не плодит сложности с certbot-sidecar.

> Альтернатива: четвёртый контейнер с Caddy/Traefik как edge. Не выбираем — увеличивает количество контейнеров.

---

## 2. Подготовка VPS (одноразово)

```bash
# Ubuntu 22.04 / 24.04 LTS как baseline.
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg ufw fail2ban

# Docker (официальный репозиторий)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Перелогиниться, чтобы группа docker подцепилась.

# Caddy для TLS на хосте
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy

# Файрвол
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Swap (важно для t2/t3 small VPS, иначе uvicorn под нагрузкой OOM-ится)
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Деплой-юзер с минимальными правами
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
sudo mkdir -p /opt/auto-report && sudo chown deploy:deploy /opt/auto-report
```

**SSH-ключ для GitHub Actions:**
1. На сервере: `sudo -u deploy ssh-keygen -t ed25519 -f ~deploy/.ssh/github_deploy -N ""`.
2. Публичную часть в `~deploy/.ssh/authorized_keys`.
3. Приватную часть положить в GitHub Secrets обоих репозиториев как `SSH_PRIVATE_KEY`.

---

## 3. Файлы, которые добавим в репозитории

### 3.1 В корень `Auto_Report/` (этот репо)

- **`Dockerfile`** — multi-stage:
  - `builder`: `python:3.11-slim` + Poetry, `poetry export` → `requirements.txt`, чтобы не таскать Poetry в runtime образ.
  - `runtime`: `python:3.11-slim`, `pip install -r requirements.txt`, копируем код, `WORKDIR /app`, `USER nobody`, `EXPOSE 8000`.
  - `CMD ["sh", "/app/docker/entrypoint.sh"]`.
- **`docker/entrypoint.sh`**:
  ```sh
  #!/bin/sh
  set -e

  # Docker secrets смонтированы как файлы в /run/secrets/.
  # Экспортируем их в env прямо перед запуском приложения — Pydantic Settings
  # и SQLAlchemy не нужно учить читать файлы. Env-переменные при этом
  # никогда не были видны в `docker inspect` / `docker compose config`.
  for f in /run/secrets/*; do
    [ -f "$f" ] || continue
    name=$(basename "$f" | tr '[:lower:]' '[:upper:]')
    export "$name"="$(cat "$f")"
  done

  alembic upgrade head
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*
  ```
- **`.dockerignore`**: `.venv`, `__pycache__`, `.git`, `logs`, `media`, `.env`, `tests`, `.pytest_cache`.
- **`docker-compose.yml`** — см. §4.
- **`docker-compose.prod.override.yml`** *(опционально)* — переопределения для прода (`restart: unless-stopped`, ресурсные лимиты).
- **`.github/workflows/deploy.yml`** — см. §6.

### 3.2 В корень `Auto_report_front/auto_report_front/`

- **`Dockerfile`** — multi-stage:
  - `builder`: `node:22-alpine`, `npm ci`, `npm run build` → `dist/`.
  - `runtime`: `nginx:1.27-alpine`, копируем `dist/` в `/usr/share/nginx/html`, копируем `docker/nginx.conf` в `/etc/nginx/conf.d/default.conf`.
- **`docker/nginx.conf`**:
  ```nginx
  server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback
    location / {
      try_files $uri $uri/ /index.html;
    }

    # Прокси к бэку (имя сервиса из docker-compose)
    location /api/ {
      proxy_pass http://backend:8000;
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_read_timeout 120s;
      client_max_body_size 50m;  # под загрузку фото вложений
    }

    # gzip и кеш для assets
    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
    location /assets/ {
      expires 30d;
      add_header Cache-Control "public, immutable";
    }
  }
  ```
- **`.dockerignore`**: `node_modules`, `dist`, `.git`.
- **`.github/workflows/deploy.yml`** — отдельный workflow для фронта.

### 3.3 Не-секретная конфигурация на VPS

Только то, что НЕ секрет:

- **`/opt/auto-report/.env`** — переменные для самого docker-compose (имя БД, версии образов, путь до секретов). Это **не пароли**:
  ```
  POSTGRES_DB=autoreport
  POSTGRES_USER=autoreport
  SECRETS_DIR=/dev/shm/auto-report-secrets
  ```
- **`/etc/caddy/Caddyfile`**:
  ```
  auto-report.example.com {
    reverse_proxy 127.0.0.1:8080
    encode gzip
  }
  ```
  (8080 — порт frontend-контейнера, см. §4).

Эти файлы НЕ в git, права `chmod 644`. Секреты — отдельно, см. §3.4.

### 3.4 Секреты — SOPS + age + Docker secrets

**Принцип, на котором всё держится:**

1. **At-rest:** все секреты хранятся в репозитории в файле `secrets/secrets.enc.yaml`, зашифрованном через **SOPS+age**. Закоммитить безопасно — без приватного age-ключа расшифровать нельзя.
2. **Доставка:** на VPS при деплое sops расшифровывает файл в **tmpfs** (`/dev/shm`), не на диск. Декрипт-ключ лежит только на VPS и на ноутбуках админов в `~/.config/sops/age/keys.txt` (`chmod 600`), вне git.
3. **Runtime:** docker-compose монтирует tmpfs-файлы как **Docker secrets** в `/run/secrets/`. Контейнер видит их как файлы, не как env-переменные → они не светятся в `docker inspect`, `docker compose config`, `ps auxe`, логах процесса, ошибках pydantic.
4. **App-side:** entrypoint бэка (см. §3.1) перед запуском uvicorn копирует `/run/secrets/*` в env — никаких правок в `config.py` и Pydantic Settings не нужно.

**Почему именно так:**

- ❌ `*.env` файлы — секреты в открытую на диске, попадают в env-переменные процесса (видны в `/proc/<pid>/environ`, `docker inspect`, в трейсах SQLAlchemy/asyncpg при ошибках подключения), легко закоммитить случайно. **Не делаем.**
- ❌ Облачный secrets-менеджер (AWS/GCP/Doppler/Infisical) — лишний сервис, vendor lock-in, ежемесячная стоимость. Для одного VPS это overkill.
- ❌ HashiCorp Vault — серьёзная инфра ради 5 секретов. Overkill.
- ✅ **SOPS+age** — один бинарь, один приватный ключ, шифрованный файл в git, расшифровка точечно при деплое. Industry-standard для GitOps на маленьких/средних инсталляциях (k3s/Flux/ArgoCD ровно так делают).
- ✅ **Docker secrets** — родной механизм docker compose, монтирует tmpfs, не env. Без Swarm работает (compose v2+).

**Структура файлов:**

```
Auto_Report/
  secrets/
    secrets.enc.yaml         ← В git. Зашифрован age.
    .sops.yaml               ← В git. Конфиг, какие ключи-получатели использовать.

# На VPS, вне git:
~deploy/.config/sops/age/keys.txt    ← Приватный age-ключ, chmod 600
/opt/auto-report/scripts/deploy.sh   ← Обёртка, см. ниже
/dev/shm/auto-report-secrets/        ← tmpfs, рантайм-расшифровка
```

**Содержимое `secrets/.sops.yaml`** (определяет, кого добавлять как получателей):

```yaml
creation_rules:
  - path_regex: secrets/secrets\.enc\.yaml$
    age: >-
      age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx,
      age1yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
```

Первый ключ — VPS, второй — ноутбук админа. Каждый может расшифровать своим приватным ключом независимо. Добавляется новый админ — публичный ключ дописывается, файл `sops updatekeys secrets/secrets.enc.yaml` перешифровывается под новый набор получателей.

**Что лежит в `secrets/secrets.enc.yaml` (после расшифровки):**

```yaml
POSTGRES_PASSWORD: "сильный-пароль-pg"
DB_PASSWORD: "тот-же-сильный-пароль-pg"
SECRET_KEY: "ротированный-2026-04-18-jwt-secret"
DB_HOST: "postgres"
DB_PORT: "5432"
DB_NAME: "autoreport"
DB_USER: "autoreport"
ALGORITHM: "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: "30"
REFRESH_TOKEN_EXPIRE_DAYS: "30"
```

> Технически `DB_HOST/PORT/NAME/USER/ALGORITHM/EXPIRE_*` — не секреты. Можно вынести их в `/opt/auto-report/.env` и `env:` блок compose, чтобы не плодить файлы в `/run/secrets/`. Решено держать всё конфиг-бэкенда в одном sops-файле — проще оперировать, и пересборка БД-параметров не требует прав на расшифровку секрета. Если хочется чище — можно разделить позже.

**Скрипт деплоя `scripts/deploy.sh` на VPS** (он же дёргается из GitHub Actions, см. §6):

```sh
#!/bin/sh
set -eu

REPO=/opt/auto-report/Auto_Report
SECRETS_DIR=/dev/shm/auto-report-secrets
SVC="${1:-}"   # backend / frontend / postgres / пусто = все

cd "$REPO"
git fetch --all
git reset --hard origin/main

# Расшифровываем в tmpfs (не на SSD!), права 700 — читает только deploy.
rm -rf "$SECRETS_DIR"
mkdir -p "$SECRETS_DIR" && chmod 700 "$SECRETS_DIR"

# По одному файлу на каждый ключ из YAML → удобно мапить в Docker secrets.
for k in $(sops -d secrets/secrets.enc.yaml | yq -r 'keys[]'); do
  sops -d --extract "[\"$k\"]" secrets/secrets.enc.yaml > "$SECRETS_DIR/$(echo "$k" | tr '[:upper:]' '[:lower:]')"
  chmod 400 "$SECRETS_DIR/$(echo "$k" | tr '[:upper:]' '[:lower:]')"
done

# Подтянули новые образы (если есть) и пересобрали нужное.
docker compose pull postgres
if [ -n "$SVC" ]; then
  docker compose up -d --build "$SVC"
else
  docker compose up -d --build
fi

docker image prune -f
```

`tmpfs` (`/dev/shm`) — критично: при перезагрузке VPS секреты исчезают и доступны снова только после следующего деплоя (recreating). На SSD ничего не остаётся.

**Установка инструментов на VPS** (одноразово):

```bash
# sops + age — официальные релизы
sudo curl -fsSL -o /usr/local/bin/sops \
  https://github.com/getsops/sops/releases/latest/download/sops-v3.9.4.linux.amd64
sudo curl -fsSL -o /usr/local/bin/age \
  https://github.com/FiloSottile/age/releases/latest/download/age-v1.2.1-linux-amd64.tar.gz   # распаковать
sudo chmod +x /usr/local/bin/sops /usr/local/bin/age

# yq для парсинга YAML
sudo curl -fsSL -o /usr/local/bin/yq \
  https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
sudo chmod +x /usr/local/bin/yq

# Сгенерировать age-ключ для VPS
sudo -u deploy mkdir -p ~deploy/.config/sops/age
sudo -u deploy age-keygen -o ~deploy/.config/sops/age/keys.txt
sudo chmod 600 ~deploy/.config/sops/age/keys.txt
# Публичную часть (строка `# public key: age1...`) — в .sops.yaml репо
```

**Ротация секрета** (например, JWT `SECRET_KEY` или БД-пароль):

1. С ноутбука админа: `sops secrets/secrets.enc.yaml` → редактируем значение → сохраняем (sops перешифрует автоматически).
2. `git commit -m "rotate: jwt secret"; git push`.
3. GitHub Actions триггерится, на VPS `scripts/deploy.sh` подхватывает свежий зашифрованный файл, расшифровывает, контейнер перезапускается с новым секретом.
4. Для БД-пароля дополнительно — `docker compose exec postgres psql -U postgres -c "ALTER USER autoreport WITH PASSWORD '<новый>'"` ДО редактирования sops-файла, иначе бэк потеряет доступ. Лучше делать в одной сессии вручную и сразу проверять.

**Резервная копия age-ключа.** Утрата приватного ключа = невозможность расшифровать `secrets.enc.yaml`. Хранить:
- Аппаратный ключ (YubiKey) — лучший вариант, age-plugin-yubikey.
- Менеджер паролей (Bitwarden/1Password) с пометкой "восстановление".
- Бумажная распечатка в сейфе для совсем большого продакшена.

> Для совсем стартового деплоя допустимый минимум: пропустить SOPS, хранить расшифрованные секреты вручную в `/opt/auto-report/secrets/` (`chmod 600`, owner `deploy`) и держать там же. Docker secrets через `secrets: { file: ... }` всё равно используем — это покрывает 90% угроз (нет env-переменных, нет вытекания в `docker inspect`). Минусы: одна копия (на VPS), не git'able, ротация только руками на сервере. **Рекомендую с SOPS, не пропускать.**

---

## 4. `docker-compose.yml` (концепт)

Лежит в корне `Auto_Report/`. Образ фронта собирается из соседней папки через `context: ../Auto_report_front/auto_report_front` — это требует, чтобы на сервере оба репо лежали рядом:

```
/opt/auto-report/
  Auto_Report/                ← бэк-репо, здесь docker-compose.yml, secrets/secrets.enc.yaml
  Auto_report_front/auto_report_front/   ← фронт-репо
  .env                        ← только несекретное (POSTGRES_DB, POSTGRES_USER, SECRETS_DIR)
  scripts/deploy.sh           ← обёртка: git pull + sops -d → /dev/shm + compose up
```

И отдельно (вне `/opt/auto-report/`):
```
~deploy/.config/sops/age/keys.txt   ← приватный age-ключ, chmod 600
/dev/shm/auto-report-secrets/       ← tmpfs, эфемерная расшифровка
```

Скелет (без полных deploy-полей):

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      # ! Postgres-образ нативно поддерживает *_FILE — читает пароль из файла.
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "${POSTGRES_USER}"]
      interval: 10s
      timeout: 3s
      retries: 5
    networks: [ar_net]

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    # ВНИМАНИЕ: никакого env_file: ./backend.env — секреты через secrets, не env.
    # Несекретное (если останется) можно держать в environment: или /opt/auto-report/.env.
    secrets:
      - db_password
      - secret_key
      - db_host
      - db_port
      - db_name
      - db_user
      - algorithm
      - access_token_expire_minutes
      - refresh_token_expire_days
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - backend_media:/app/media
      - backend_logs:/app/logs
    networks: [ar_net]
    # внутрь сети, наружу не публикуем — доступ только через frontend-nginx

  frontend:
    build:
      context: ../Auto_report_front/auto_report_front
      dockerfile: Dockerfile
    restart: unless-stopped
    depends_on:
      - backend
    ports:
      - "127.0.0.1:8080:80"   # слушает только loopback, Caddy с хоста проксирует
    networks: [ar_net]

# Файлы секретов лежат в tmpfs на VPS (см. §3.4), путь — переменная SECRETS_DIR
# из /opt/auto-report/.env. Compose ругнётся, если файла нет — это намеренно:
# деплоить нельзя, не положив секреты.
secrets:
  postgres_password:
    file: ${SECRETS_DIR}/postgres_password
  db_password:
    file: ${SECRETS_DIR}/db_password
  secret_key:
    file: ${SECRETS_DIR}/secret_key
  db_host:
    file: ${SECRETS_DIR}/db_host
  db_port:
    file: ${SECRETS_DIR}/db_port
  db_name:
    file: ${SECRETS_DIR}/db_name
  db_user:
    file: ${SECRETS_DIR}/db_user
  algorithm:
    file: ${SECRETS_DIR}/algorithm
  access_token_expire_minutes:
    file: ${SECRETS_DIR}/access_token_expire_minutes
  refresh_token_expire_days:
    file: ${SECRETS_DIR}/refresh_token_expire_days

volumes:
  pg_data:
  backend_media:
  backend_logs:

networks:
  ar_net:
    driver: bridge
```

Решения, заложенные в этот скелет:
- `postgres` НЕ публикует 5432 наружу — он доступен только бэку по docker-сети.
- `backend` НЕ публикует 8000 — доступен только через frontend-nginx (тот же origin → нет проблем с CORS).
- `frontend` слушает только `127.0.0.1:8080`, наружу 80/443 отдаёт Caddy с TLS.
- `media` и `logs` — named volumes, переживают пересборку контейнера.
- `depends_on: postgres { condition: service_healthy }` — бэкенд ждёт готовности БД (и не падает в alembic).

---

## 5. Миграции и первичная инициализация

- `entrypoint.sh` бэка вызывает `alembic upgrade head` ДО запуска uvicorn. На каждом деплое миграции применяются автоматически.
- Первый запуск: контейнер бэка увидит чистую БД и накатит все миграции с нуля.
- Создание первого админа: добавить отдельную скрипт-команду (`poetry run python -m scripts.seed_admin`) или ручной `docker compose exec backend python -c "..."`. В план: создать `scripts/seed_admin.py` ОДНИМ из следующих PR.

---

## 6. Автодеплой через GitHub Actions

**Стратегия: SSH-деплой.** Workflow в каждом из двух репо при push в `main` ходит на сервер по SSH, делает `git pull` и `docker compose up -d --build` нужного сервиса. Никакого registry — образы собираются на VPS.

`.github/workflows/deploy.yml` в обоих репозиториях — короткий, вся логика в `scripts/deploy.sh` на VPS (см. §3.4):

```yaml
name: Deploy
on:
  push:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: deploy-${{ github.repository }}
  cancel-in-progress: false   # не отменять текущий деплой — дать ему закончиться

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: SSH and deploy
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: deploy
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            /opt/auto-report/scripts/deploy.sh backend
            # для фронт-workflow: deploy.sh frontend
```

GitHub Secrets в обоих репозиториях — **только** доступы для SSH:
- `SSH_HOST` — IP/DNS VPS.
- `SSH_PRIVATE_KEY` — приватная часть ключа `deploy@vps`.

**Важно: никаких production-секретов в GitHub Secrets.** `POSTGRES_PASSWORD`, `SECRET_KEY` и прочее лежат в SOPS-файле на VPS и в репо как зашифрованный артефакт. GitHub видит только SSH-ключ, который сам по себе даёт доступ только на запуск `deploy.sh` (если ещё ограничить через `command="..."` в `authorized_keys` — вообще ничего, кроме одной команды).

Дополнительно стоит **ограничить SSH-ключ одной командой** в `~deploy/.ssh/authorized_keys`:
```
command="/opt/auto-report/scripts/deploy.sh ${SSH_ORIGINAL_COMMAND}",no-pty,no-agent-forwarding,no-port-forwarding ssh-ed25519 AAAA...
```
Тогда даже если GitHub-секрет SSH утечёт, атакующий не сможет получить shell — только запустить deploy.sh с конкретным аргументом.

> Почему SSH, а не Container Registry + Watchtower:
> - Не требует GHCR-аккаунта и публикации образов.
> - Минимум инфры; деплой = пуш в main.
> - Минус: сборка съедает CPU на VPS. Если VPS совсем маленький — переключиться на «билд в Actions → push в GHCR → docker compose pull на VPS».

**Concurrency-замок** не даёт параллельным workflow'ам одновременно дёргать `docker compose up -d --build`. `cancel-in-progress: false` важен — нельзя обрывать сборку посреди.

**Healthcheck после деплоя** (опционально, в конце скрипта):
```bash
timeout 60 bash -c 'until curl -fsS http://127.0.0.1:8080/api/docs > /dev/null; do sleep 2; done'
```
Если упадёт — Actions workflow fail → видно в GitHub.

---

## 7. Обновления и откат

- Каждый коммит в `main` → новый Docker-образ собирается на VPS, старый контейнер заменяется.
- Откат: SSH на сервер, `cd /opt/auto-report/Auto_Report && git reset --hard <предыдущий-sha> && docker compose up -d --build backend`. Подкладывать ярлык типа `release-stable` (тегом) можно, но не обязательно.
- БД-откат миграций НЕ автоматический — это намеренно. Если миграция плохая, нужно вручную `alembic downgrade -1` внутри контейнера.

---

## 8. Бэкапы

**PostgreSQL** — обязательно. Минимальный вариант: cron на хосте, ежедневно в 03:00:

```bash
0 3 * * * docker exec ar-postgres pg_dump -U autoreport autoreport \
  | gzip > /opt/auto-report/backups/autoreport-$(date +\%F).sql.gz \
  && find /opt/auto-report/backups -mtime +14 -delete
```

Дополнительно — синк backups на S3/Backblaze/любое внешнее хранилище (`rclone sync`). Без off-site бэкапа полный отказ VPS = потеря всего.

**Volume `backend_media`** (загруженные PDF-вложения отчётов и заявок) — тоже бэкапить, тем же cron:
```bash
0 3 * * * tar -czf /opt/auto-report/backups/media-$(date +\%F).tar.gz \
  -C /var/lib/docker/volumes/auto-report_backend_media/_data .
```

---

## 9. Наблюдаемость и логи

- `backend_logs` volume содержит loguru-логи (см. `logs/`). Ротация — встроенная (loguru может настроить retention).
- `docker compose logs -f backend` для оперативного просмотра.
- Docker по умолчанию пишет JSON-логи в `/var/lib/docker/containers/...` — настроить `logging.options.max-size: "50m"` в `/etc/docker/daemon.json`, иначе диск переполнится.

### 9.1. UptimeRobot (внешний uptime-monitoring)

Бесплатный план — до 50 мониторов, интервал ≥5 минут, нотификации по email.

**Что мониторим:** `https://<ваш-домен>/api/health` (на боевом VDS — `https://hi-tech.cool-doc.ru/api/health`). Endpoint без авторизации и без БД-запросов, отдаёт `{"status":"ok"}`, проверяет всю цепочку Caddy → frontend-nginx → uvicorn → handler.

**Настройка монитора:**
1. Зарегистрироваться на [uptimerobot.com](https://uptimerobot.com), подтвердить email.
2. **+ New Monitor** → `Monitor Type: HTTP(s)`, `Friendly Name: Auto_Report VDS`, `URL: https://<домен>/api/health`, `Monitoring Interval: 5 minutes`, в `Alert Contacts` отметить свой email. **Create Monitor**.
3. (опционально) **Keyword Check** → искать `ok` — защищает от ситуации «200 OK с битым контентом».

**Грабли free-плана:**
- UptimeRobot **free** шлёт **HEAD**, не GET (выбор метода — только в платном Pro). FastAPI-роут с одиночным `@router.get(...)` на HEAD возвратит `405 Method Not Allowed` → монитор зависнет в `Down`.
- В нашем `main.py` healthcheck объявлен как `@app.api_route("/api/health", methods=["GET", "HEAD"])` — оба метода отдают одинаковый JSON, монитор сразу видит `Up`. Если копируешь паттерн в новый endpoint — не забудь HEAD.

**Сетевое:**
- UptimeRobot пингует с пула IP (US/EU/AS). Если в Caddy/UFW добавляли rate-limit или geo-фильтры — проверь что они не блокируют UptimeRobot. Список IP — на их сайте в Docs.

---

## 10. Безопасность

**Секреты:**
- `POSTGRES_PASSWORD`, `SECRET_KEY` и прочие — в `secrets/secrets.enc.yaml` (зашифровано SOPS+age, лежит в git). Расшифровка только на VPS, в **tmpfs** (`/dev/shm`), не на SSD.
- Подача в контейнеры — через **Docker secrets** (файлы в `/run/secrets/`), не через env. Это значит:
  - Нет в выводе `docker inspect`, `docker compose config`.
  - Нет в `/proc/<pid>/environ` других процессов.
  - Нет в логах при ошибке подключения SQLAlchemy/asyncpg (raw DSN не дампится).
  - Не утекают в stacktrace pydantic при невалидной конфигурации.
- Приватный age-ключ хранится только на VPS (`~deploy/.config/sops/age/keys.txt`, `chmod 600`) и у админов локально. Не в git, не в GitHub Secrets, не в docker-образах.
- GitHub Secrets содержит **только** `SSH_PRIVATE_KEY` и `SSH_HOST` — этого достаточно для запуска `deploy.sh`, но недостаточно для расшифровки секретов.

**Транспорт:**
- Caddy сам обновляет TLS-сертификаты (Let's Encrypt ACME).
- SSH-ключ деплоя ограничен одной командой через `authorized_keys` (`command="..."`).

**Сетевая поверхность:**
- Postgres без `ports:` — доступен только из docker-сети.
- Backend без `ports:` — только через frontend-nginx (proxy).
- Frontend на `127.0.0.1:8080` — снаружи виден только через Caddy на 443.
- UFW открывает 22/80/443, остальное закрыто.

**Хост:**
- fail2ban защищает SSH от перебора.
- Регулярные `apt upgrade` (или `unattended-upgrades` для security-only).
- Отдельный непривилегированный пользователь `deploy` владеет `/opt/auto-report/` и docker-группой.

---

## 11. Чек-лист первого деплоя

1. ☐ Прогнать §2 на свежем VPS (docker, Caddy, ufw, swap, deploy-юзер).
2. ☐ Купить/настроить DNS-запись `auto-report.example.com` → IP VPS.
3. ☐ Установить sops/age/yq на VPS (см. §3.4, блок «Установка инструментов»). Сгенерировать age-ключ для `deploy`. Сохранить публичную часть.
4. ☐ На локальной машине админа: установить sops+age, сгенерировать свой age-ключ. Сохранить публичную часть.
5. ☐ В репо `Auto_Report/secrets/.sops.yaml` положить оба публичных ключа. Создать `secrets/secrets.enc.yaml` командой `sops secrets/secrets.enc.yaml` (sops откроет редактор, заполнить значениями из §3.4). Закоммитить оба файла.
6. ☐ Положить `Dockerfile`, `docker/entrypoint.sh`, `docker-compose.yml`, `.dockerignore`, `scripts/deploy.sh` в `Auto_Report/`. Закоммитить.
7. ☐ Положить `Dockerfile`, `docker/nginx.conf`, `.dockerignore` в фронт-репо. Закоммитить.
8. ☐ От имени `deploy` на VPS: `cd /opt/auto-report && git clone <backend-repo> Auto_Report && git clone <frontend-repo> Auto_report_front`.
9. ☐ Создать `/opt/auto-report/.env` (только несекретное: `POSTGRES_DB`, `POSTGRES_USER`, `SECRETS_DIR=/dev/shm/auto-report-secrets`).
10. ☐ Сделать `scripts/deploy.sh` исполняемым; запустить вручную `bash /opt/auto-report/scripts/deploy.sh`. Проверить, что secrets расшифровались в `/dev/shm/auto-report-secrets/` (`ls -la`, должны быть `chmod 400` файлы), и `docker compose ps` показывает три healthy-контейнера.
11. ☐ Создать первого админа (`docker compose exec backend python -m scripts.seed_admin`).
12. ☐ Настроить `/etc/caddy/Caddyfile`, `sudo systemctl reload caddy`. Открыть `https://auto-report.example.com` — должен отдаться SPA, JWT-логин работать.
13. ☐ Ограничить SSH-ключ деплоя одной командой через `authorized_keys` (см. §6).
14. ☐ Положить `SSH_HOST`, `SSH_PRIVATE_KEY` в GitHub Secrets обоих репо, добавить `.github/workflows/deploy.yml`, сделать тестовый коммит в main — убедиться что Actions работает end-to-end.
15. ☐ Завести cron-бэкапы (§8). Бэкапить ОТДЕЛЬНО: `pg_data`, `backend_media`, `secrets/secrets.enc.yaml` (последний — ради истории, расшифровка всё равно нужна с age-ключом).
16. ☐ Зарезервировать копию age-ключа `~deploy/.config/sops/age/keys.txt` офф-сайт (Bitwarden/YubiKey/бумага в сейф).
17. ☐ Подключить UptimeRobot (§9).

---

## 12. Открытые вопросы для согласования

Перед началом реализации нужно от тебя решение по:

1. **Хостинг и домен.** Какой провайдер (Hetzner / Selectel / Timeweb / другое)? Есть ли уже домен? Без них дальше не двигаемся.
2. **Размер VPS.** Минимум: 2 vCPU, 2 GB RAM, 40 GB SSD — этого хватит на малую нагрузку с запасом на сборку образов. Если VPS меньше (1 GB) — придётся вынести сборку в GitHub Actions + GHCR (см. §6).
3. **SSL-домен.** Если домена не будет (только IP) — Caddy не сможет получить Let's Encrypt; придётся либо self-signed (браузер будет ругаться), либо http-only (плохо — JWT в открытую). Сильно рекомендую купить домен.
4. **Два репо или один?** Сейчас бэк и фронт — отдельные репозитории. Это работает (две workflow'и), но добавляет копий конфигов. Альтернатива — monorepo + один docker-compose. Если не планируется монорепо — оставляем как есть.
5. **Пункт #14 (пароль БД на проде 192.168.1.8).** Текущий прод-сервер `192.168.1.8` останется, или новый VPS его заменит? Если заменит — пункт #14 неактуален в момент переезда (на VPS пароль сразу сильный); если параллельно — пункт #14 остаётся как был.
6. **Объём `media/`.** Сколько вложений ожидается в год? От этого зависит размер диска и стратегия бэкапа (мелкие — тарбол; крупные — synced объектное хранилище).
7. **Создание первого админа.** Сделать ли в плане скрипт `scripts/seed_admin.py` (читает имя/пароль из env при первом запуске) или достаточно ручного `docker compose exec`? Первое удобнее для CI, но требует одного дополнительного PR.

---

## Связанные документы

- `CLAUDE.md` — структура проекта, конвенции.
- `..\Auto_report_front\auto_report_front\CLAUDE.md` — структура фронта.
- Открытое: #14 — смена пароля БД на текущем проде `192.168.1.8` (`ALTER USER autoreport WITH PASSWORD '…'` + обновить `.env` на старом проде). На новом VPS этот пункт неактуален с момента переезда — сильный пароль ставится сразу через SOPS-файл, ротация делается процедурой из §3.4.
