from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, update as sqlalchemy_update, delete as sqlalchemy_delete
from database.database import async_session_maker

from model.user import User

from utils.timer import timer




class BaseDAO:
    """
    Базовый класс для Data Access Object (DAO).
    Предоставляет общие CRUD-операции для моделей SQLAlchemy.
    Для использования в дочерних классах необходимо определить атрибут model.
    """
    model = None  # Должен быть переопределён в дочернем классе

    @classmethod
    async def get_all(cls):
        """
        Возвращает список всех записей модели.
        """
        async with async_session_maker() as session:
            query = select(cls.model)
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def find_all(cls, **filter_by):
        """
        Возвращает список записей, удовлетворяющих условиям фильтрации.
        """
        async with async_session_maker() as session:
            query = select(cls.model).filter_by(**filter_by)
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def find_one_or_none_by_id(cls, data_id: int):
        """
        Возвращает одну запись по её id или None, если запись не найдена.
        """
        async with async_session_maker() as session:
            query = select(cls.model).filter_by(id=data_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    @classmethod
    async def find_one_or_none_by_name(cls, data_name: str):
        """
        Возвращает одну запись по её name или None, если запись не найдена.
        """
        async with async_session_maker() as session:
            query = select(cls.model).filter_by(name=data_name)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    @classmethod
    async def find_one_or_none(cls, **filter_by):
        """
        Возвращает одну запись, соответствующую фильтру, или None.
        Если фильтру соответствует несколько записей, возвращается первая.
        """
        async with async_session_maker() as session:
            query = select(cls.model).filter_by(**filter_by)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    @classmethod
    async def add(cls, **values):
        """
        Создаёт новую запись и возвращает её.
        """
        async with async_session_maker() as session:
            async with session.begin():
                new_instance = cls.model(**values)
                session.add(new_instance)
                try:
                    await session.commit()
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e
                return new_instance

    @classmethod
    async def update(cls, filter_by: dict, **values):
        """
        Обновляет записи, соответствующие фильтру.
        Возвращает количество обновлённых записей.
        """
        async with async_session_maker() as session:
            async with session.begin():
                query = (
                    sqlalchemy_update(cls.model)
                    .filter_by(**filter_by)
                    .values(**values)
                    .execution_options(synchronize_session="fetch")
                )
                result = await session.execute(query)
                try:
                    await session.commit()
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e
                return result.rowcount

    @classmethod
    async def delete(cls, **filter_by):
        """
        Удаляет записи, соответствующие фильтру.
        Возвращает количество удалённых записей.
        """
        if not filter_by:
            raise ValueError("Необходимо указать хотя бы один параметр для удаления.")

        async with async_session_maker() as session:
            async with session.begin():
                query = sqlalchemy_delete(cls.model).filter_by(**filter_by)
                result = await session.execute(query)
                try:
                    await session.commit()
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e
                return result.rowcount

class UsersDAO(BaseDAO):
    model = User

    @classmethod
    async def find_with_role(cls, **filter_by):
        """Находит пользователя и подгружает его роль."""
        async with async_session_maker() as session:
            query = (
                select(cls.model)
                .filter_by(**filter_by)
                .options(selectinload(cls.model.role))   # явная загрузка связи
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()