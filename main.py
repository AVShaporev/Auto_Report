from contextlib import asynccontextmanager
from typing import AsyncGenerator
from os import getcwd
import sys

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import (
                    FastAPI,
                    Request,
                    Response,
                    Depends
                    )
from loguru import logger

from api import spec_contract as api_spec_contract
from api import contract as api_contract
from api import spec_job_title as api_spec_job_title
from api import spec_equipment as api_spec_equipment
from api import bank as api_bank
from api import auth as api_user_auth
from api import role as api_role
from api import user as api_user


# настройка файлов логирования
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Удаляем стандартный вывод
logger.remove()

# Добавляем вывод в консоль
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}",
    level="INFO",
    colorize=True
)

# Добавляем вывод в файл с ротацией
logger.add(
    LOG_DIR / "app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {message}",
    level="INFO",
    rotation="10 MB",  # Ротация при достижении 10 MB
    retention="30 days",  # Хранить 30 дней
    compression="zip",  # Сжимать старые файлы
    encoding="utf-8"
)

logger.info("🚀 Логирование Loguru настроено")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    """Управление жизненным циклом приложения."""
    logger.info("Инициализация приложения...")
    yield
    logger.info("Завершение работы приложения...")

# объект приложения FastAPI
app = FastAPI(lifespan=lifespan,
                title="AutoReport API",
                description="API с Bearer-аутентификацией",
                swagger_ui_init_oauth={
                    "usePkceWithAuthorizationCodeGrant": True,
                    "clientId": "swagger"
                })

# добавление субмаршрутов из уровня api
app.include_router(api_spec_contract.router)
app.include_router(api_contract.router)
app.include_router(api_spec_job_title.router)
app.include_router(api_spec_equipment.router)
app.include_router(api_bank.router)
app.include_router(api_user_auth.router)
app.include_router(api_role.router)
app.include_router(api_user.router)

# запуск приложения fastapi
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)