from typing import Optional, List, Dict, Any, Tuple

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, update, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from model.user import User
from model.role import Role
from schema.user import (
                            Read_User,
                            UserBase,
                            UserRequest,
                            UserUpdate,
                            UserResponse
                        )


from utils.timer import timer

@timer
# Функция добавления строки в БД
async def create(
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
async def get_all(session: AsyncSession):
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
async def get_all_paginated(
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
async def get_one_by_name(
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
async def get_one_by_id(
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
async def get_one_by_email(
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
async def modify(
                    session: AsyncSession,
                    user: User
                    ):
    query = select(User).where(User.name == user.name)
    res = await session.execute(query)
    orig_user = res.scalars(res).one()
    orig_user.name = creature.name
    orig_user.hash = creature.country
    orig_user.userrole = creature.area
    await session.commit()
    return await get_one(orig_user.name)

@timer
async def delete_by_name(
                            session: AsyncSession,
                            name: str
                            ) -> bool:
    """
        Удалить пользователи по имени (name)
    """
    user = await get_one(name)
    await session.delete(user)
    await session.commit()
    return True

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
        print(error)
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
async def update_user(
                        session: AsyncSession,
                        user_id: int,
                        user_update: UserUpdate
                    ) -> Optional[User]:
    """
    Обновить пользователя по ID
    
    Args:
        session: Сессия БД
        user_id: ID пользователя
        user_update: Данные для обновления (Pydantic схема)
    
    Returns:
        Обновленный пользователь или None если не найден
    """
    # 1. Получаем пользователя
    user = await get_user(session, user_id, load_relations=False)
    if not user:
        return None
    
    # 2. Получаем данные для обновления (только переданные поля)
    update_data = user_update.dict(exclude_unset=True)
    
    # 3. Проверка уникальности (если меняются уникальные поля)
    if any(field in update_data for field in ['name', 'email', 'phone', 'telegram_id']):
        error = await check_user_exists(
            session,
            name=update_data.get('name'),
            email=update_data.get('email'),
            phone=update_data.get('phone'),
            telegram_id=update_data.get('telegram_id'),
            exclude_id=user_id
        )
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
    
    # 4. Проверка существования роли (если меняется)
    if 'role_id' in update_data:
        if not await check_role_exists(session, update_data['role_id']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Роль с id {update_data['role_id']} не существует"
            )
    
    # 5. Обработка пароля
    if 'password' in update_data:
        update_data['hash'] = get_password_hash(update_data.pop('password'))
    
    # 6. Обновляем поля
    for field, value in update_data.items():
        setattr(user, field, value)
    
    # 7. Сохраняем
    await session.commit()
    await session.refresh(user)
    
    # 8. Загружаем отношения
    result = await session.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.role))
    )
    return result.scalar_one()

@timer
async def patch_user(
                        session: AsyncSession,
                        user_id: int,
                        updates: Dict[str, Any]
                    ) -> Optional[User]:
    """
    Частичное обновление пользователя из словаря
    
    Args:
        session: Сессия БД
        user_id: ID пользователя
        updates: Словарь с полями для обновления
    """
    user = await get_user(session, user_id, load_relations=False)
    if not user:
        return None
    
    # Фильтруем только поля, которые есть в модели
    model_columns = {c.name for c in User.__table__.columns}
    
    for field, value in updates.items():
        if field in model_columns and value is not None:
            if field == 'password':
                setattr(user, 'hash', get_password_hash(value))
            else:
                setattr(user, field, value)
    
    await session.commit()
    await session.refresh(user)
    
    # Загружаем отношения
    result = await session.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.role))
    )
    return result.scalar_one()

@timer
async def delete_by_id(
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
    user = await get_one_by_id(user_id)
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