import os
from pathlib import Path
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
    return (f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@"
            f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

def get_auth_data():
    return {
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
            "secret_key": settings.SECRET_KEY, 
            "algorithm": settings.ALGORITHM
            }