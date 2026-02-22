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
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from web import organization as web_organization
from web import contract as web_contract
from web import sub_contract as web_sub_contract
from web import myobject as web_object
from web import report as web_report
from web import order as web_order
from web import equipment as web_equipment
from web import objects_equipment as web_objects_equipment
from web import locality as web_locality
from web import user as web_user
from web import spec_contract as web_spec_contract

from api import spec_contract as api_spec_contract
from api import contract as api_contract
from api import spec_job_title as api_spec_job_title
from api import spec_equipment as api_spec_equipment
from api import bank as api_bank
from api import auth as api_user_auth
from api import role as api_role
from api import user as api_user

from service.user import get_all as get_all_users
from service.auth import (
                            get_current_admin_user,
                            get_current_user
)

from model.user import User

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

# # логирование
# def setup_logging():
#     log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     # Корневой логгер
#     root_logger = logging.getLogger()
#     root_logger.setLevel(logging.INFO)
    
#     # Хендлер для файла с ротацией
#     file_handler = RotatingFileHandler(
#         LOG_DIR / "app.log",
#         maxBytes=10*1024*1024, # 10 MB
#         backupCount=5
#     )
#     file_handler.setFormatter(logging.Formatter(log_format))
#     root_logger.addHandler(file_handler)
    
#     # Хендлер для консоли (полезно для разработки)
#     console_handler = logging.StreamHandler()
#     console_handler.setFormatter(logging.Formatter(log_format))
#     root_logger.addHandler(console_handler)
    
#     # Логгер для SQLAlchemy (чтобы видеть запросы в DEBUG режиме)
#     logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    """Управление жизненным циклом приложения."""
    logger.info("Инициализация приложения...")
    res = await get_all_users()
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

# добавление субмаршрутов из уровня web
app.include_router(web_organization.router)
app.include_router(web_contract.router)
app.include_router(web_sub_contract.router)
app.include_router(web_object.router)
app.include_router(web_report.router)
app.include_router(web_order.router)
app.include_router(web_equipment.router)
app.include_router(web_objects_equipment.router)
app.include_router(web_locality.router)
app.include_router(web_user.router)
app.include_router(web_spec_contract.router)

# добавление субмаршрутов из уровня api
app.include_router(api_spec_contract.router)
app.include_router(api_contract.router)
app.include_router(api_spec_job_title.router)
app.include_router(api_spec_equipment.router)
app.include_router(api_bank.router)
app.include_router(api_user_auth.router)
app.include_router(api_role.router)
app.include_router(api_user.router)

# настройка приложения FastAPI для обслуживания статических файлов
staticfiles = StaticFiles(directory='templates/static/')
app.mount('/static', staticfiles, name='static')

# указание пути для шаблонов Jinja2
templates = Jinja2Templates(directory='templates')

# главная страница
@app.get("/")
async def main_page(request: Request, user: User = Depends(get_current_user)):
    
    return templates.TemplateResponse(name='index.html',
                                        context={'request': request, 
                                                    'user': user})

# страница "о проекте"
@app.get("/about")
async def about_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(name='about.html',
                                        context={'request': request, 
                                                    'user': user})

# страница контактов
@app.get("/contact")
async def about_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(name='contact.html',
                                        context={'request': request, 
                                                    'user': user})

# страница отдела
@app.get("/team")
async def about_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(name='team.html',
                                        context={'request': request, 
                                                    'user': user})

# страница входа
@app.get("/login")
async def about_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(name='login.html',
                                        context={'request': request, 
                                                    'user': user})

# страница входа
@app.get("/logout")
async def about_page(request: Request, user: User = Depends(get_current_user)):
    res = templates.TemplateResponse(name='index.html',
                                        context={'request': request})
    res.delete_cookie(key="users_access_token")
    return res

# страница списков
@app.get('/lists')
async def lists_page(request: Request,
                        response: Response,
                        user: User = Depends(get_current_admin_user),
                        current_user: User = Depends(get_current_admin_user)):
    is_superadmin = True
    
    if current_user:
        is_superadmin = True

    return templates.TemplateResponse(name='lists.html',
                                        context={'request': request,
                                                'user': user,
                                                'is_superadmin': is_superadmin})

# Скачивание файла
@app.get("/download_file", response_class=FileResponse)
async def main():
    path = getcwd()
    some_file_path=path+'\\templates\\static\\img\\Logo_Hi-Tech_Sec_grey_grad.png'
    return some_file_path

# запуск приложения fastapi
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)