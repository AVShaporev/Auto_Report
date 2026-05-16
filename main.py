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

from config import MEDIA_PATH
from middleware import LogRequestsMiddleware

from api import spec_contract as api_spec_contract
from api import contract as api_contract
from api import sub_contract as api_sub_contract
from api import spec_job_title as api_spec_job_title
from api import spec_equipment as api_spec_equipment
from api import equipment as api_equipment
from api import operation as api_operation
from api import spec_order as api_spec_order
from api import spec_system as api_spec_system
from api import order as api_order
from api import report as api_report
from api import report_attachment as api_report_attachment
from api import bank as api_bank
from api import spec_region as api_spec_region
from api import region as api_region
from api import spec_arial as api_spec_arial
from api import arial as api_arial
from api import spec_locality as api_spec_locality
from api import locality as api_locality
from api import spec_street as api_spec_street
from api import street as api_street
from api import spec_build as api_spec_build
from api import spec_room as api_spec_room
from api import auth as api_user_auth
from api import role as api_role
from api import user as api_user
from api import organization as api_organization
from api import period as api_period
from api import object as api_object
from api import issue as api_issue
from api import objects_equipment as api_objects_equipment
from api import dashboard  as api_dashboard
from api import log as api_log



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
    MEDIA_PATH.mkdir(parents=True, exist_ok=True)
    logger.info(f"MEDIA_PATH: {MEDIA_PATH}")
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

# Добавляем middleware до подключения роутеров
app.add_middleware(LogRequestsMiddleware)

# добавление субмаршрутов из уровня api
app.include_router(api_spec_contract.router)
app.include_router(api_contract.router)
app.include_router(api_sub_contract.router)
app.include_router(api_spec_job_title.router)
app.include_router(api_spec_equipment.router)
app.include_router(api_equipment.router)
app.include_router(api_operation.router)
app.include_router(api_spec_order.router)
app.include_router(api_spec_system.router)
app.include_router(api_order.router)
app.include_router(api_report.router)
app.include_router(api_report_attachment.router)
app.include_router(api_spec_region.router)
app.include_router(api_spec_locality.router)
app.include_router(api_locality.router)
app.include_router(api_spec_street.router)
app.include_router(api_street.router)
app.include_router(api_spec_build.router)
app.include_router(api_spec_room.router)
app.include_router(api_region.router)
app.include_router(api_spec_arial.router)
app.include_router(api_arial.router)
app.include_router(api_bank.router)
app.include_router(api_user_auth.router)
app.include_router(api_role.router)
app.include_router(api_user.router)
app.include_router(api_organization.router)
app.include_router(api_period.router)
app.include_router(api_object.router)
app.include_router(api_issue.router)
app.include_router(api_objects_equipment.router)
app.include_router(api_dashboard.router)
app.include_router(api_log.router)

# запуск приложения fastapi
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)