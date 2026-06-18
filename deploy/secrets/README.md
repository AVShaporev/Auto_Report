# deploy/secrets/

Здесь лежат зашифрованные через SOPS+age `.env`-файлы для каждого
окружения. **Сырые `.env` сюда не кладём** — только `.env.sops`.

## Соглашения по именованию

```
deploy/secrets/
  vds-prod.env.sops      # /opt/auto-report/.env на 188.120.227.138
  192-stage.env.sops     # /etc/autoreport/stage.env на 192.168.1.8
  192-prod.env.sops      # /etc/autoreport/prod.env на 192.168.1.8
  # …позже…
  tenants/
    acme.env.sops        # per-tenant SaaS-секреты
    contoso.env.sops
```

## Просмотр содержимого

```bash
# Подразумевается, что приватный age-ключ лежит в:
#   ~/.config/sops/age/keys.txt   (локально)
#   /etc/sops/age/keys.txt         (на сервере)
# SOPS находит его автоматически.

sops --input-type dotenv --output-type dotenv -d deploy/secrets/vds-prod.env.sops
```

## Редактирование

```bash
# Открывает в $EDITOR, после сохранения — re-encrypt.
sops deploy/secrets/vds-prod.env.sops
```

## Шифрование нового файла

```bash
# Получаем сырой .env (например, с сервера), шифруем, удаляем сырой:
sops --input-type dotenv --output-type dotenv -e ./tmp-raw.env > deploy/secrets/vds-prod.env.sops
rm ./tmp-raw.env
```

## Деплой

`scripts/deploy_vds.sh` (см. Этап 0.6) перед `docker compose up`
дешифрует нужный файл во временный `/tmp/auto-report-deploy.env`
с правами 0600, экспортирует переменные, удаляет файл.

## Ротация

Процедуры ротации секретов (отдельных значений, master age-ключа, аварийный
сценарий) описаны в [ROTATION.md](./ROTATION.md).

## Связано

- `../../.sops.yaml` — конфиг recipient'а и path-regex'ов
- [ROTATION.md](./ROTATION.md) — ротация ключей и секретов
- memory `autoreport-saas-roadmap` — почему так
