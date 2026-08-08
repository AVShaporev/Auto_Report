import os
from pathlib import Path
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    MEDIA_ROOT: str = "./media"
    # Включён ли cron-tick auto-генерации заявок в lifespan'е приложения.
    # На dev-машине можно отключить через AUTOGEN_SCHEDULER_ENABLED=false,
    # чтобы не зависеть от системного времени. В prod/stage — оставить True.
    AUTOGEN_SCHEDULER_ENABLED: bool = True
    # SaaS-лимиты тарифа. Прокидываются master'ом через .env при provision'е
    # tenant'а (см. Auto_Report_Master/scripts/provision-tenant.sh). На pre-SaaS
    # инстансах (hi-tech) и в dev'е переменные не выставлены → Optional/None →
    # лимиты не enforce'атся, баннер не показывается.
    TENANT_SLUG: str | None = None
    TENANT_PLAN: str | None = None
    MAX_OBJECTS: int | None = None
    MAX_USERS: int | None = None
    # Mobile M1.6 QR-onboarding. Shared secret между master'ом и tenant'ом
    # для подписи короткоживущих onboard-JWT. Master в env
    # MOBILE_ONBOARD_SECRET подписывает — tenant этим же ключом проверяет.
    # Если не задан → /api/auth/mobile-onboard возвращает 503.
    # provision-tenant.sh прокидывает secret из master-env для новых
    # tenant'ов; существующим нужно добавить руками в .env.sops + redeploy.
    MOBILE_ONBOARD_SECRET: str | None = None
    # CORS: доп-origins через запятую для dev/smoke mobile-app'а (например
    # "https://192.168.1.3:5174,https://192.168.1.5:5174"). Прод-регекс уже
    # покрывает capacitor://localhost, https://localhost, *.cool-doc.ru —
    # см. main.py add_middleware(CORSMiddleware).
    EXTRA_CORS_ORIGINS: str = ""
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    )

settings = Settings()

# Абсолютный путь к корню для пользовательских файлов (PDF-вложения отчётов и т.п.)
MEDIA_PATH: Path = Path(settings.MEDIA_ROOT)
if not MEDIA_PATH.is_absolute():
    MEDIA_PATH = (Path(__file__).resolve().parent / MEDIA_PATH).resolve()

# Подпапка для .docx/.dotx-шаблонов, привязанных к типам заявок (spec_order).
# Заполняется деплой-скриптом (cp -n из templates/seeds/) + загрузками админа через UI.
MEDIA_TEMPLATES_PATH: Path = MEDIA_PATH / "templates"
MEDIA_TEMPLATES_PATH.mkdir(parents=True, exist_ok=True)



def get_db_url():
    # URL-encode пользователя и пароль: base64-пароли содержат +/= (все они
    # reserved-symbols в URL), а трейлинг \r/\n от sops/sed редактирования
    # тоже ломает URL-парсер asyncpg → он отправляет в БД усечённый пароль
    # и получает InvalidPassword. quote(safe='') кодирует всё что нельзя.
    user = quote(settings.DB_USER, safe='')
    password = quote(settings.DB_PASSWORD, safe='')
    return (f"postgresql+asyncpg://{user}:{password}@"
            f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

def get_auth_data():
    return {
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
            "secret_key": settings.SECRET_KEY, 
            "algorithm": settings.ALGORITHM
            }