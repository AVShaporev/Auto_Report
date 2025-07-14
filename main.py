from contextlib import asynccontextmanager
from typing import AsyncGenerator
from os import getcwd

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
from web import equipment as web_equipment
from web import objects_equipment as web_objects_equipment
from web import locality as web_locality

from service.user import get_all as get_all_users
from service.auth import (
                            get_current_admin_user,
                            get_current_user
)

from model.user import User


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    """Управление жизненным циклом приложения."""
    logger.info("Инициализация приложения...")
    res = await get_all_users()
    # print(res)
    yield
    logger.info("Завершение работы приложения...")

# объект приложения FastAPI
app = FastAPI(lifespan=lifespan)

# добавление субмаршрутов из уровня web
app.include_router(web_organization.router)
app.include_router(web_contract.router)
app.include_router(web_sub_contract.router)
app.include_router(web_object.router)
app.include_router(web_equipment.router)
app.include_router(web_objects_equipment.router)
app.include_router(web_locality.router)

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