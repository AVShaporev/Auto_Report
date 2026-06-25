from typing import Optional, List, Dict, Any, Tuple

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, update, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from model.user import User
from model.role import Role
from schema.user import UserRequest


from utils.timer import timer

async def count_users(session: AsyncSession) -> int:
    """Сколько пользователей всего в БД tenant'а. Используется в Etap 4 SaaS
    для enforcement MAX_USERS и в /api/tenant/limits."""
    return (await session.scalar(select(func.count()).select_from(User))) or 0


@timer
# Функция добавления строки в БД
async def add_user(
                    session: AsyncSession,
                    user: User) -> bool:
    """
        Создать пользователя в БД
    """
    session.add(user)
    await session.flush()
    await session.commit()
    return True

@timer
# Функция проверки на наличие уникальности полей 
#   при создании или изменении пользователя
async def check_user_exists(
    session: AsyncSession,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    telegram_id: Optional[str] = None,
    exclude_id: Optional[int] = None
) -> Optional[str]:
    """
    Проверка уникальности полей пользователя
    
    Returns:
        Сообщение об ошибке или None если всё ок
    """
    # async with new_session() as session:
    if name:
        query = select(User).where(User.name == name)
        if exclude_id:
            query = query.where(User.id != exclude_id)
        result = await session.execute(query)
        if result.scalar_one_or_none():
            return f"Пользователь с именем '{name}' уже существует"
    
    if email:
        query = select(User).where(User.email == email)
        if exclude_id:
            query = query.where(User.id != exclude_id)
        result = await session.execute(query)
        if result.scalar_one_or_none():
            return f"Пользователь с email '{email}' уже существует"
    
    if phone:
        query = select(User).where(User.phone == phone)
        if exclude_id:
            query = query.where(User.id != exclude_id)
        result = await session.execute(query)
        if result.scalar_one_or_none():
            return f"Пользователь с телефоном '{phone}' уже существует"
    
    if telegram_id:
        query = select(User).where(User.telegram_id == telegram_id)
        if exclude_id:
            query = query.where(User.id != exclude_id)
        result = await session.execute(query)
        if result.scalar_one_or_none():
            return f"Пользователь с Telegram ID '{telegram_id}' уже существует"
    
    return None

@timer
# Функция проверки существования роли для пользователя
async def check_role_exists(
                            session: AsyncSession,
                            role_id: int) -> bool:
    """Проверка существования роли"""
    # async with new_session() as session:
    result = await session.execute(select(Role).where(Role.id == role_id))
    return result.scalar_one_or_none() is not None

@timer
# Функция получения списка всех пользователй из БД
async def get_user_all(session: AsyncSession):
    """
        Получить список всех пользователей
    """
    users = None
    query = select(User)
    res = await session.execute(query)
    users = res.scalars().all()
    # users = [user for user in users if user.name != 'superadmin']
    return users

@timer
async def get_user_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    role_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    sort_by: str = "id",
    sort_order: str = "asc"
) -> Tuple[List[User], int]:
    """
    Получить список пользователей с пагинацией
    """
    # Базовый запрос
    query = select(User)
    count_query = select(func.count()).select_from(User)
    
    # Поиск
    if search:
        search_filter = or_(
            User.name.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтры
    if role_id:
        query = query.where(User.role_id == role_id)
        count_query = count_query.where(User.role_id == role_id)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    # Сортировка
    if sort_by and hasattr(User, sort_by):
        column = getattr(User, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    
    # Пагинация
    query = query.offset(skip).limit(limit)
    
    # Выполнение
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    return items, total

@timer
async def get_user_by_name(
                            session: AsyncSession,
                            name: str) -> User:
    """
        Получить пользователя по имени (name)
    """
    query = select(User).filter(
                            User.name == name
                            )
    res = await session.execute(query)
    user = res.scalars().one_or_none()
    return user

@timer
async def get_user_by_id(
                        session: AsyncSession,
                        id: int) -> User:
    """
        Получить пользователя по id
    """
    query = select(User).filter(
                            User.id == id
                            )
    res = await session.execute(query)
    user = res.scalars().one_or_none()
    return user

@timer
async def get_user_by_email(
                            session: AsyncSession,
                            email: str) -> User:
    """
        Получить пользователя по email
    """
    query = select(User).filter(
                            User.email == email
                            )
    res = await session.execute(query)
    user = res.scalars().one_or_none()
    return user

@timer
async def update_user(
                    session: AsyncSession,
                    user_id: int,
                    updates: Dict[str, Any],
                    ) -> Optional[User]:
    """
    Частичное обновление пользователя по id.
    updates — dict с полями, которые клиент явно прислал
    (из Pydantic: `.dict(exclude_unset=True)`). Возвращает обновлённого User
    с подгруженной role, либо None, если пользователь не найден.
    """
    # 1. Берём пользователя по id.
    user = await get_user_by_id(session, user_id)
    if not user:
        return None

    # 2. Чистим поля, которые менять нельзя/нельзя через setattr:
    #    - id — pk, меняться не должен.
    #    - role — это relationship, не колонка; клиент может прислать
    #      вложенный объект role, его игнорируем (роль меняется через role_id).
    updates = {k: v for k, v in updates.items() if k not in ('id', 'role')}

    # 3. Если пришёл raw-password, кладём его хеш в колонку hash.
    #    Импорт локальный, чтобы избежать циклического импорта
    #    (service.auth импортирует model.dao → model.user → ...).
    if updates.get('password'):
        from service.auth import get_password_hash
        updates['hash'] = get_password_hash(updates.pop('password'))
    else:
        updates.pop('password', None)

    # 4. Прогоняем через белый список колонок модели,
    #    чтобы случайно не присвоить что-то постороннее.
    model_columns = {c.name for c in User.__table__.columns}
    for field, value in updates.items():
        if field in model_columns and value is not None:
            setattr(user, field, value)

    await session.commit()
    await session.refresh(user)

    # 5. Догружаем role для нормальной сериализации через UserResponse.
    result = await session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.role))
    )
    return result.scalar_one()

@timer
async def create_user(
                        session: AsyncSession,
                        user_create: UserRequest
                        ) -> User:
    """
    Создать нового пользователя
    
    Args:
        session: Сессия БД
        user_create: Данные для создания
    
    Returns:
        Созданный пользователь
    
    Raises:
        HTTPException: если данные не уникальны или роль не существует
    """
    # 1. Проверка уникальности
    error = await check_user_exists(
        session,
        name=user_create.name,
        email=user_create.email,
        phone=user_create.phone,
        telegram_id=user_create.telegram_id
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # 2. Проверка существования роли
    if not await check_role_exists(session, user_create.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Роль с id {user_create.role_id} не существует"
        )
    
    # 3. Создание пользователя
    # user_data = user_create.dict(exclude={'password'})
    # user_data['hash'] = get_password_hash(user_create.password)
    
    # user = User(**user_data)
    session.add(user_create)
    await session.commit()
    await session.refresh(user_create)
    
    # 4. Загружаем отношения
    result = await session.execute(
        select(User)
        .where(User.id == user_create.id)
        .options(selectinload(User.role))
    )
    return result.scalar_one()

@timer
async def delete_user(
                        session: AsyncSession,
                        user_id: int
                        # soft_delete: bool = True
                    ) -> bool:
    """
    Удалить пользователя
    
    Args:
        session: Сессия БД
        user_id: ID пользователя
        soft_delete: Если True - только деактивировать, если False - удалить из БД
    
    Returns:
        True если успешно, False если пользователь не найден
    """
    # Было `get_one_by_id(user_id)` без session — TypeError при вызове
    # (у get_one_by_id сигнатура `(session, id)`). Исправлено.
    user = await get_user_by_id(session, user_id)
    if not user:
        return False
    
    # if soft_delete:
    #     # Мягкое удаление (деактивация)
    #     user.is_active = False
    #     await session.commit()
    # else:
    # Полное удаление
    await session.delete(user)
    await session.commit()
    
    return True