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

from config import MEDIA_PATH, settings
from middleware import LogRequestsMiddleware
from service.order_autogen import tick_planned_orders

from api import spec_contract as api_spec_contract
from api import contract as api_contract
from api import sub_contract as api_sub_contract
from api import spec_job_title as api_spec_job_title
from api import spec_equipment as api_spec_equipment
from api import equipment as api_equipment
from api import operation as api_operation
from api import spec_order as api_spec_order
from api import spec_status as api_spec_status
from api import spec_priority as api_spec_priority
from api import spec_journal as api_spec_journal
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
from api import issue_attachment as api_issue_attachment
from api import objects_equipment as api_objects_equipment
from api import dashboard  as api_dashboard
from api import log as api_log
from api import autogen as api_autogen
from api import tenant as api_tenant



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

# Добавляем вывод в файл с ротацией.
# enqueue=True — пишем через фоновую очередь: один writer-thread владеет файлом,
# остальные процессы (uvicorn reload spawn'ит worker; antivirus; VS Code, держащий
# app.log открытым на просмотр) не конкурируют за хэндл. Без этого на Windows
# rotation падает с WinError 32 (file locked by another process) на os.rename.
# delay=True — не открывать файл до первой записи (reloader-процесс может и не
# дойти до неё). catch=True — rotation-ошибка не должна валить приложение.
logger.add(
    LOG_DIR / "app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {message}",
    level="INFO",
    rotation="10 MB",  # Ротация при достижении 10 MB
    retention="30 days",  # Хранить 30 дней
    compression="zip",  # Сжимать старые файлы
    encoding="utf-8",
    enqueue=True,
    delay=True,
    catch=True,
)

logger.info("🚀 Логирование Loguru настроено")

async def _autogen_tick_job() -> None:
    """Cron-обёртка для tick_planned_orders. Сама не падает — нужно ОЧЕНЬ
    стараться, чтобы APScheduler не выбросил job-failure при первой ошибке
    (он по умолчанию backoff'ает повторы и спамит логи)."""
    try:
        result = await tick_planned_orders()
        logger.info(f"🗓 autogen-tick: {result.summary()}")
        for err in result.errors:
            logger.warning(f"🗓 autogen-tick error: {err}")
    except Exception as e:
        logger.exception(f"🗓 autogen-tick упал: {e}")


async def _push_tokens_cleanup_job() -> None:
    """Ежедневная чистка push_tokens с last_seen_at > 30 дней. Токен,
    в который FCM/APNs больше не доставляет, всё равно бесполезен."""
    try:
        from database.database import new_session
        from data import push_token as push_token_dao
        async with new_session() as session:
            deleted = await push_token_dao.cleanup_stale_push_tokens(
                session, max_age_days=30
            )
        logger.info(f"🔔 push-tokens cleanup: удалено {deleted}")
    except Exception as e:
        logger.exception(f"🔔 push-tokens cleanup упал: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    """Управление жизненным циклом приложения."""
    logger.info("Инициализация приложения...")
    MEDIA_PATH.mkdir(parents=True, exist_ok=True)
    logger.info(f"MEDIA_PATH: {MEDIA_PATH}")

    # APScheduler для авто-генерации плановых заявок (раз в сутки, 00:30 МСК).
    # На stage/prod settings.AUTOGEN_SCHEDULER_ENABLED=True; на dev можно
    # выключить через .env, чтобы не зависеть от системного времени.
    scheduler = None
    if settings.AUTOGEN_SCHEDULER_ENABLED:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
        scheduler.add_job(
            _autogen_tick_job,
            trigger=CronTrigger(hour=0, minute=30),
            id="autogen_tick",
            replace_existing=True,
            misfire_grace_time=3600,  # терпит downtime до часа без skip'а
            coalesce=True,             # пропустил 3 запуска подряд — выполнит один
        )
        scheduler.add_job(
            _push_tokens_cleanup_job,
            trigger=CronTrigger(hour=3, minute=15),
            id="push_tokens_cleanup",
            replace_existing=True,
            misfire_grace_time=3600,
            coalesce=True,
        )
        scheduler.start()
        logger.info(
            "🗓 APScheduler запущен: autogen-tick 00:30 МСК + push-tokens cleanup 03:15 МСК"
        )
    else:
        logger.info("🗓 APScheduler выключен (AUTOGEN_SCHEDULER_ENABLED=False)")

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("🗓 APScheduler остановлен")
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


# Healthcheck endpoint без авторизации, без БД-запросов.
# Используется GitHub Actions deploy-vds.yml workflow'ами и Dockerfile
# HEALTHCHECK для проверки доступности бэка после rebuild.
# HEAD-дубль нужен для UptimeRobot free plan, который шлёт только HEAD
# (на GET-only роут возвращался бы 405 → "Down").
@app.api_route("/api/health", methods=["GET", "HEAD"], tags=["Health"])
async def health_check():
    return {"status": "ok"}


# добавление субмаршрутов из уровня api
app.include_router(api_spec_contract.router)
app.include_router(api_contract.router)
app.include_router(api_sub_contract.router)
app.include_router(api_spec_job_title.router)
app.include_router(api_spec_equipment.router)
app.include_router(api_equipment.router)
app.include_router(api_operation.router)
app.include_router(api_spec_order.router)
app.include_router(api_spec_status.router)
app.include_router(api_spec_priority.router)
app.include_router(api_spec_journal.router)
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
app.include_router(api_issue_attachment.router)
app.include_router(api_objects_equipment.router)
app.include_router(api_dashboard.router)
app.include_router(api_log.router)
app.include_router(api_autogen.router)
app.include_router(api_tenant.router)

# запуск приложения fastapi
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)