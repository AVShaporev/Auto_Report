from typing import Optional, List, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select

from model.user import User
from model.report import Report
from model.order import Order
from model.issue import Issue

from schema.user import UserRequest
from schema.pagination import PaginationParams

from data import user as data

from database.database import async_session_maker as new_session

from service.auth import get_password_hash


# Поля, которые НЕЛЬЗЯ менять у is_protected=True юзера через update.
# Личные данные (full_name, email, phone, telegram_id, password) — можно.
_PROTECTED_USER_LOCKED_FIELDS = {'name', 'role_id', 'is_active'}


async def get_one(name: str):
    async with new_session() as session:
        try:
            id = int(name)
            user = await data.get_user_by_id(session, name)
            return user
        except:
            name = str(name)
            user = await data.get_user_by_name(session, name)
            return user


async def create(user_create: UserRequest) -> bool:
    """
    Создание пользователя из Pydantic схемы

    Args:
        user_create: Pydantic схема с данными пользователя

    Returns:
        bool: True если создан успешно
    """
    async with new_session() as session:
        # 1. Преобразуем Pydantic модель в SQLAlchemy модель
        user_data = user_create.dict(exclude={'password'})  # исключаем пароль

        # 2. Создаем SQLAlchemy модель User
        user = User(
            name=user_data['name'],
            full_name=user_data.get('full_name'),
            email=user_data.get('email'),
            phone=user_data.get('phone'),
            telegram_id=user_data.get('telegram_id'),
            role_id=user_data['role_id'],
            is_active=user_data['is_active'],
            hash=get_password_hash(user_create.password)  # хешируем пароль отдельно
        )

        # 3. Передаем SQLAlchemy модель в data слой
        res = await data.create_user(session, user)
        return res

async def get_all():
    # при отсутвтии в БД суперадмина завести superadmin и в командной
    # строке указать пароль для него
    async with new_session() as session:
        exist_super = await get_one('superadmin')
        if exist_super is None:
            password = input('Введите пароль для пользователя superadmin: ')
            superadmin = User(
                name='superadmin',
                role_id=1,
                is_active=True,
                hash=get_password_hash(password),
            )
            await data.add_user(session, superadmin)
        users = await data.get_user_all(session)
        return users

async def delete_by_id(id: int):
    async with new_session() as session:
        existing = await data.get_user_by_id(session, id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Пользователь с id {id} не найден")
        if existing.is_protected:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить защищённого пользователя '{existing.name}' — "
                       f"он необходим для работы системы.",
            )

        # Подсчёт связанных записей. FK у reports.user_id, orders.user_id,
        # issues.reported_by_id, issues.assigned_to_id (последний nullable —
        # технически можно было бы зануллить, но прозрачнее блокировать
        # удаление и попросить переназначить вручную).
        related = await _count_user_dependencies(session, id)
        if related:
            blocks = ", ".join(f"{label}: {count}" for label, count in related)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Невозможно удалить пользователя '{existing.name}' — у него "
                    f"есть связанные записи ({blocks}). Переназначьте/удалите их "
                    f"или деактивируйте пользователя (статус «Неактивен») вместо удаления."
                ),
            )

        res = await data.delete_user(session, id)
        return res


async def _count_user_dependencies(session, user_id: int) -> list[tuple[str, int]]:
    """Возвращает список (label, count) ненулевых FK-зависимостей юзера."""
    pairs = [
        ("отчётов", await session.scalar(
            select(func.count()).select_from(Report).where(Report.user_id == user_id)
        )),
        ("заявок", await session.scalar(
            select(func.count()).select_from(Order).where(Order.user_id == user_id)
        )),
        ("созданных неисправностей", await session.scalar(
            select(func.count()).select_from(Issue).where(Issue.reported_by_id == user_id)
        )),
        ("назначенных неисправностей", await session.scalar(
            select(func.count()).select_from(Issue).where(Issue.assigned_to_id == user_id)
        )),
    ]
    return [(label, count) for label, count in pairs if count and count > 0]


async def modify(user_id: int, user) -> Optional[User]:
    """
    Обновить пользователя.
    `user` — Pydantic-схема (UserUpdate, UserResponse и т.п.). В data-слой
    уходит dict только с теми полями, которые клиент явно прислал
    (`exclude_unset=True`), чтобы PUT по ошибке не затирал остальные.
    Возвращает обновлённого User или None, если не найден.

    Для is_protected=True юзера блокируем смену name / role_id / is_active —
    остальное (full_name, email, phone, telegram_id, password) разрешено,
    чтобы суперадмин мог обновить личные данные и ротировать пароль.
    """
    async with new_session() as session:
        updates = (
            user.dict(exclude_unset=True)
            if hasattr(user, 'dict') else dict(user)
        )

        existing = await data.get_user_by_id(session, user_id)
        if existing is None:
            return None

        if existing.is_protected:
            blocked = _PROTECTED_USER_LOCKED_FIELDS & updates.keys()
            if blocked:
                raise HTTPException(
                    status_code=400,
                    detail=f"У защищённого пользователя '{existing.name}' нельзя "
                           f"менять поля: {', '.join(sorted(blocked))}.",
                )

        return await data.update_user(session, user_id=user_id, updates=updates)

async def get_users_paginated(
    pagination: PaginationParams,
    search: Optional[str] = None,
    role_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    sort_by: str = "id",
    sort_order: str = "asc"
) -> Tuple[List[User], int]:
    """
    Получить список пользователей с пагинацией
    """
    # Сессия управляется контекстным менеджером ниже.
    # Раньше в data.get_user_paginated передавался `session=new_session()` —
    # это открывало ВТОРУЮ параллельную сессию на каждый запрос (фабрика
    # вызывалась ещё раз), первая сессия от `async with` оставалась неиспользованной.
    # Теперь прокидываем именно ту сессию, которой владеет контекстный менеджер.
    async with new_session() as session:
        users, total = await data.get_user_paginated(
            session=session,
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            role_id=role_id,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return users, total
