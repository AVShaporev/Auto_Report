from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.database import async_session_maker
from model.user import User
from model.spec_equipment import Spec_Equipment
from data.base import BaseDAO


class UsersDAO(BaseDAO):
    """
    DAO для работы с моделью User.
    """
    model = User

    @classmethod
    async def find_with_role(cls, **filter_by):
        """
        Находит пользователя по фильтру и подгружает связанную роль.
        Возвращает один объект User или None.
        """
        async with async_session_maker() as session:
            query = (
                select(cls.model)
                .filter_by(**filter_by)
                .options(selectinload(cls.model.role))   # явная загрузка отношения role
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()


class SpecEquipmentDAO(BaseDAO):
    """
    DAO для работы с моделью Spec_Equipment.
    """
    model = Spec_Equipment