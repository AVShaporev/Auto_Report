# deploy/192-server-scripts/

Версионированные копии скриптов с сервера 192.168.1.8 (`/opt/autoreport/scripts/`)
плюс sudoers-фрагменты. На самом сервере эти файлы должны соответствовать
содержимому этой директории — git выступает только источником истории, не
читается сервером.

## Файлы

| Файл | Куда кладётся на сервере | Mode | Owner |
|---|---|---|---|
| `install-env-file.sh` | `/opt/autoreport/scripts/install-env-file.sh` | 0755 | root:root |
| `sudoers-github-runner-sops` | `/etc/sudoers.d/github-runner-sops` | 0440 | root:root |
| `deploy-backend.sh` | `/opt/autoreport/scripts/deploy-backend.sh` | 0755 | root:root |

`scripts/decrypt-env.sh` (из корня репо) уже подтягивается в `$REPO/scripts/`
каждым `git pull` — отдельно копировать не нужно.

## Раскатка на 192.168.1.8 (Этап 0.8, разовая операция)

Предполагается, что:
- Sops 3.10.2 + age уже установлены (`which sops age` → пути есть).
- На сервер уже скопирован приватный age-ключ в `/etc/sops/age/keys.txt`,
  mode 0640, owner `root:github-runner`. См. отдельный шаг ниже.
- В `deploy/secrets/` уже коммитнуты `192-stage.env.sops` и `192-prod.env.sops`.

```bash
# 1. Положить приватный age-ключ.
#    Файл переносится с локальной машины (где лежит у тебя в Bitwarden /
#    ~/.config/sops/age/keys.txt) через scp — не через этот чат.
scp ~/.config/sops/age/keys.txt ashaporev@192.168.1.8:/tmp/keys.txt
ssh -t ashaporev@192.168.1.8 '
  sudo mkdir -p /etc/sops/age
  sudo install -m 640 -o root -g github-runner /tmp/keys.txt /etc/sops/age/keys.txt
  shred -u /tmp/keys.txt
  sudo ls -la /etc/sops/age/keys.txt
'

# 2. Скопировать helper + sudoers + новый deploy-backend.sh.
#    Делается с локальной машины — файлы берутся из репо (ветка stage).
PROJECT=...  # путь до Auto_Report в твоём шелле
scp "$PROJECT/deploy/192-server-scripts/install-env-file.sh"        ashaporev@192.168.1.8:/tmp/
scp "$PROJECT/deploy/192-server-scripts/sudoers-github-runner-sops" ashaporev@192.168.1.8:/tmp/
scp "$PROJECT/deploy/192-server-scripts/deploy-backend.sh"          ashaporev@192.168.1.8:/tmp/deploy-backend.sh.new

ssh -t ashaporev@192.168.1.8 '
  # helper
  sudo install -m 0755 -o root -g root /tmp/install-env-file.sh /opt/autoreport/scripts/install-env-file.sh

  # sudoers (visudo -c -f валидирует перед установкой — если упадёт, файл не появится)
  sudo install -m 0640 -o root -g root /tmp/sudoers-github-runner-sops /tmp/sudoers-staging
  sudo visudo -c -f /tmp/sudoers-staging
  sudo install -m 0440 -o root -g root /tmp/sudoers-staging /etc/sudoers.d/github-runner-sops
  sudo rm /tmp/sudoers-staging

  # deploy-backend.sh — бэкап старого + новый
  sudo cp /opt/autoreport/scripts/deploy-backend.sh /opt/autoreport/scripts/deploy-backend.sh.bak.$(date +%Y%m%d-%H%M%S)
  sudo install -m 0755 -o root -g root /tmp/deploy-backend.sh.new /opt/autoreport/scripts/deploy-backend.sh

  # чистим /tmp
  rm /tmp/install-env-file.sh /tmp/sudoers-github-runner-sops /tmp/deploy-backend.sh.new

  # быстрая sanity-проверка
  sudo -u github-runner -- /opt/autoreport/scripts/decrypt-env.sh --help 2>&1 || true
'

# 3. Проверить, что github-runner может расшифровать stage env (round-trip без перезапуска сервиса).
#    Это безопасно — мы ничего не пишем в /etc/autoreport/.
ssh -t ashaporev@192.168.1.8 '
  cd /opt/autoreport/stage/backend
  sudo -u github-runner -- scripts/decrypt-env.sh 192-stage > /dev/null
  echo "decrypt ok: $?"
  sudo -u github-runner -- ls -la /tmp/auto-report-deploy.192-stage.env
  sudo -u github-runner -- rm /tmp/auto-report-deploy.192-stage.env
'
```

## Триггер первого деплоя по SOPS-флоу

После раскатки выше — запустить deploy через `workflow_dispatch` на stage:

```
GitHub → Actions → Deploy backend → Run workflow → branch=stage, env=stage
```

В логах должно появиться:
```
[sops] decrypt + install /etc/autoreport/stage.env
[install-env-file] /tmp/auto-report-deploy.192-stage.env -> /etc/autoreport/stage.env (root:autoreport 640)
```

После успешного деплоя — повторить для prod (merge stage→prod, тот же workflow).

## Что менять при ротации секретов

Источник истины — `deploy/secrets/192-{stage,prod}.env.sops`. Редактирование:

```bash
sops deploy/secrets/192-stage.env.sops
# (откроет $EDITOR, сохрани — заново зашифрует под текущий .sops.yaml recipient)
git add deploy/secrets/192-stage.env.sops
git commit -m "secrets: rotate ... in 192-stage"
git push origin stage
```

Дальше обычный merge → prod → автодеплой. Подробнее — [`../secrets/ROTATION.md`](../secrets/ROTATION.md).
