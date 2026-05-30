from datetime import datetime
from typing import Annotated
import contextlib

from sqlalchemy import func
from sqlalchemy.ext.asyncio import (
                                    create_async_engine,
                                    async_sessionmaker, 
                                    AsyncAttrs,
                                    AsyncSession
                                    )
from sqlalchemy.orm import (
                            DeclarativeBase,
                            declared_attr,
                            Mapped,
                            mapped_column
                            )

from config import get_db_url

DATABASE_URL = get_db_url()


# Создаем engine и sessionmaker
engine = create_async_engine(
                                DATABASE_URL,
                                # echo=True,  # Показывает все SQL запросы
                                # pool_size=5,
                                # max_overflow=10
                                )

# Диагностический счётчик SQL-запросов на HTTP-запрос — используется middleware
from utils.sql_counter import install as _install_sql_counter
_install_sql_counter(engine)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# # Правильная зависимость для FastAPI
# async def get_async_session() -> AsyncSession:
#     """
#     Зависимость для получения сессии БД
#     """
#     async with AsyncSessionLocal() as session:
#         yield session  # Важно: yield, не return!
#         # Сессия автоматически закроется после завершения запроса

@contextlib.asynccontextmanager
async def new_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session

        finally:
            await session.close()

# настройка аннотаций
int_pk = Annotated[int, mapped_column(primary_key=True)]
created_at = Annotated[datetime, mapped_column(server_default=func.now())]
updated_at = Annotated[datetime, mapped_column(server_default=func.now(), onupdate=datetime.now)]
str_uniq = Annotated[str, mapped_column(unique=True, nullable=False)]
str_null_true = Annotated[str, mapped_column(nullable=True)]
int_null_true = Annotated[int, mapped_column(nullable=True)]
str_description = Annotated[str, mapped_column(unique=False, nullable=True)]

class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}s"

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]
    description: Mapped[str_description]