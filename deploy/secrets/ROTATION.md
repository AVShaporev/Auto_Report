# Ротация SOPS-секретов

Документ описывает три сценария:

1. [Ротация одного секрета внутри `.env.sops`](#1-ротация-одного-секрета-например-secret_key)
2. [Ротация master age-ключа](#2-ротация-master-age-ключа)
3. [Аварийный сценарий: master age-ключ потерян / скомпрометирован полностью](#3-аварийный-сценарий-master-age-ключ-потерян)

Все процедуры предполагают, что Этап 0 SOPS+age уже раскатан end-to-end:

- `.sops.yaml` лежит в корне репо
- `deploy/secrets/<env>.env.sops` — зашифрованные блоки
- `scripts/decrypt-env.sh` и `deploy_vds.sh` интегрированы
- На целевых серверах `/etc/sops/age/keys.txt` (mode 0640 `root:deploy`)

---

## 1. Ротация одного секрета (например `SECRET_KEY`)

Самый частый случай: подозрение что значение «утекло» (попало в логи / контекст моделей / чужой git stash), либо просто плановая ротация.

### Шаги

1. **Сгенерировать новое значение** локально:

   ```bash
   # SECRET_KEY (JWT)
   python -c "import secrets; print(secrets.token_urlsafe(64))"

   # POSTGRES_PASSWORD / DB_PASSWORD
   python -c "import secrets; print(secrets.token_urlsafe(32))"

   # ADMIN_PASSWORD
   python -c "import secrets; print(secrets.token_urlsafe(24))"
   ```

2. **Открыть нужный `.env.sops` для редактирования**:

   ```bash
   # Локально (приватник в ~/.config/sops/age/keys.txt или %APPDATA%\sops\age\keys.txt)
   sops deploy/secrets/vds-prod.env.sops
   ```

   SOPS дешифрует, откроет в `$EDITOR` (nano/vim), при сохранении — заново зашифрует под публичный age-ключ из `.sops.yaml`. Сырое значение никуда на диск не уходит.

3. **Сохранить, выйти из редактора**. SOPS перепишет файл с новым `data:` блоком.

4. **Закоммитить и запушить**:

   ```bash
   git add deploy/secrets/vds-prod.env.sops
   git commit -m "secrets: rotate SECRET_KEY (yyyy-mm-dd)"
   # без указания значения в сообщении!
   git push origin stage
   ```

5. **Особые случаи отдельных секретов** — см. ниже.

6. **Merge → prod, деплой** (как обычный релиз). На VDS:
   - `deploy_vds.sh` → `decrypt-env.sh` достанет новое значение в `/tmp/auto-report-deploy.vds-prod.env`
   - `docker compose up -d --build backend` поднимет новый контейнер с уже новыми переменными
   - Trap удалит временный файл

7. **Verify**:

   ```bash
   # На VDS под deploy
   docker exec auto-report-backend env | grep -E 'SECRET_KEY|DB_PASSWORD'
   # Должны быть новые значения. Желательно не показывать их кому попало в shared shell.
   ```

### Особенности конкретных секретов

| Секрет | Что ещё нужно сделать |
|---|---|
| **`SECRET_KEY`** (JWT) | Ничего. Все юзеры разлогинятся (старые JWT инвалидируются), зайдут заново со своими паролями — bcrypt-хеши в `users.hash` не зависят от `SECRET_KEY`. |
| **`POSTGRES_PASSWORD` / `DB_PASSWORD`** | **Синхронно сделать `ALTER USER` в Postgres** — иначе после перезапуска backend не подключится к БД. См. ниже. |
| **`ADMIN_PASSWORD`** | На уже инициализированной БД ничего не делает — `bootstrap_admin.py` создаёт юзера только на пустой схеме. Чтобы реально сменить пароль суперадмина — отдельной командой через UI или `data/user.update_user`. |
| **`ALGORITHM`**, токен-TTL, прочие нечувствительные | Просто меняем и переезжаем. |

### `DB_PASSWORD` — синхронная смена пароля в Postgres

```bash
# Перед редактированием .env.sops зайди в pg и поменяй пароль
docker exec -it auto-report-postgres psql -U autoreport -d autoreport \
  -c "ALTER USER autoreport WITH PASSWORD '<НОВЫЙ-ПАРОЛЬ>';"

# Дальше — sops <file>, обновляем POSTGRES_PASSWORD и DB_PASSWORD на то же значение, коммит/пуш/деплой
```

**Порядок важен**: сначала ALTER, потом редактируем SOPS, иначе следующий перезапуск backend упадёт «password authentication failed» и `set -e` оставит контейнер в неподнятом состоянии.

Если нужно сделать без даунтайма — Postgres поддерживает множественные роли. Создай временную роль `autoreport_temp` с тем же набором прав, переключи backend на неё, потом ALTER оригинала.

---

## 2. Ротация master age-ключа

Сценарий: приватная часть age-ключа попала куда не надо (закоммитили в чужой репо, кто-то другой получил доступ к Bitwarden), но **она ещё цела** у нас и расшифровать `.env.sops` мы можем.

Цель — сменить master-ключ так, чтобы все ранее зашифрованные файлы перешифровались под новый recipient.

### Шаги

1. **Сгенерировать новый age-ключ**:

   ```bash
   age-keygen -o ~/age-new.txt
   # Файл содержит:
   #   # created: <date>
   #   # public key: age1...        ← это публичка, идёт в .sops.yaml
   #   AGE-SECRET-KEY-1...           ← приватник, идёт в Bitwarden + на серверы
   ```

   Запиши публичную часть отдельно — пригодится на шаге 4.

2. **Сохранить новый приватник в Bitwarden** под именем
   `autoreport-sops-age-master` (заменив старый), плюс в `~/.config/sops/age/keys.txt`
   (или `%APPDATA%\sops\age\keys.txt` для Windows).

3. **На каждом сервере** (VDS + 192.168.1.8 stage + 192.168.1.8 prod) — добавить
   новый ключ в `/etc/sops/age/keys.txt`. Можно ОДНОЙ КОМАНДОЙ дописать после старого
   (sops понимает несколько identity в файле):

   ```bash
   # на сервере, под root
   echo '' >> /etc/sops/age/keys.txt
   cat ~/age-new.txt | head -3 | tail -1 >> /etc/sops/age/keys.txt  # одна строка с AGE-SECRET-KEY
   ```

   На этом шаге сервера принимают **оба** ключа — старый ещё валиден для расшифровки. Это даёт нам окно для перешифровки без даунтайма.

4. **Обновить `.sops.yaml`** в репо — заменить публичную часть в `age:` строке:

   ```yaml
   creation_rules:
     - path_regex: '\.env(\.[a-zA-Z0-9_-]+)?$'
       age: age1NEW_PUBLIC_KEY_HERE  # ← новая публичка с шага 1
   ```

5. **Перешифровать все `.env.sops`-файлы** одной командой (со старым приватником в keys.txt):

   ```bash
   sops updatekeys deploy/secrets/*.env.sops
   # На каждый файл sops спросит "Y/n?" — отвечаем Y. Содержимое не показывается.
   ```

   Эта команда оставляет содержимое неизменным, просто меняет `recipients:` блок в YAML-хедере файла.

6. **Закоммитить и запушить**:

   ```bash
   git add .sops.yaml deploy/secrets/*.env.sops
   git commit -m "secrets: rotate master age key (yyyy-mm-dd)"
   git push origin stage
   ```

7. **Merge → prod, деплой**. На VDS `decrypt-env.sh` подхватит файлы — он сможет расшифровать и новым, и старым ключом (оба лежат в `/etc/sops/age/keys.txt`).

8. **После успешного деплоя и проверки** — удалить старый ключ с серверов и из локального keychain:

   ```bash
   # На каждом сервере: убрать строку со старым AGE-SECRET-KEY
   sudo nano /etc/sops/age/keys.txt
   # Удалить блок старого ключа, оставить только новый

   # Локально: то же самое
   nano ~/.config/sops/age/keys.txt
   ```

9. **Bitwarden cleanup** — старая запись `autoreport-sops-age-master-OLD` (если сохраняли) удаляется. Срок жизни — не больше недели после успешного деплоя.

---

## 3. Аварийный сценарий: master age-ключ потерян

Сценарий: приватной части age-ключа больше нет нигде (Bitwarden очищен, локальные копии стёрты, сервер переустановлен). Расшифровать существующие `.env.sops` **невозможно**.

Это не разрушительная катастрофа — содержимое `.env.sops` восстановимо из памяти / документации (тип секретов известен, формат тоже), но потребует ручной работы.

### Восстановление

1. **Сгенерировать новый ключ**, положить в Bitwarden + локально (как в [§2](#2-ротация-master-age-ключа), шаги 1–2).

2. **Обновить `.sops.yaml`** на новую публичку.

3. **Сгенерировать новые значения для всех секретов** (всё как в [§1](#1-ротация-одного-секрета-например-secret_key)):

   - `POSTGRES_PASSWORD` / `DB_PASSWORD` — новый, сразу `ALTER USER` в pg
   - `SECRET_KEY` — новый, все JWT инвалидируются
   - `ADMIN_PASSWORD` — новый
   - Прочие нечувствительные (`DB_HOST`, `DB_PORT`, `DB_NAME`, `ALGORITHM`, токен-TTL) — взять из старого `docker-compose.yml` / `config.py`

4. **Создать новый `.env`-файл локально** (например `/tmp/restored.env`), записать туда все эти переменные.

5. **Зашифровать в `.env.sops`**:

   ```bash
   sops --input-type dotenv --output-type dotenv -e /tmp/restored.env > deploy/secrets/vds-prod.env.sops
   shred -u /tmp/restored.env   # надёжно затереть исходник
   ```

6. **Дальше как обычный rollout**: commit, push, merge prod, deploy.

7. **После успешного входа в UI** проверить, что суперадмин зайти не может со старым паролем — это подтверждение что новый `ADMIN_PASSWORD` применён (только при первом запуске на пустой схеме, см. оговорку в §1). Если БД сохранилась — суперадмин по-прежнему логинится по своему bcrypt-хешу из таблицы, новый `ADMIN_PASSWORD` его не затронет.

---

## Контроль качества ротации

После любой из трёх процедур — **независимая проверка** что новое значение действительно применилось:

```bash
# 1. На VDS под deploy
docker exec auto-report-backend env | grep SECRET_KEY | head -1
# Если значение совпадает с тем что в Bitwarden / в локальном дешифровке — порядок.

# 2. Тестовый логин в UI с реальным юзер-паролем —
#    подтверждает что backend перезапустился и читает новый .env.

# 3. Если ротировался DB_PASSWORD — проверить что бэкап работает:
sudo -iu deploy /opt/auto-report/scripts/backup.sh
# Не должен ругаться "password authentication failed".
```

## Связано

- `../../.sops.yaml` — конфиг recipient'ов
- `README.md` — соглашения по именованию `.env.sops`-файлов
- `../../scripts/decrypt-env.sh` — расшифровка на деплое
- `../../scripts/deploy_vds.sh` — интеграция в pipeline
- memory `autoreport-saas-roadmap` — Этап 0 SOPS+age и пометки про засветившиеся секреты
