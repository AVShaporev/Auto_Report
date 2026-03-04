from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from model.role import Role
from model.user import User
from schema.role import RoleCreate, RoleUpdate

# ========== ПОЛУЧЕНИЕ ==========

async def get_by_id(
    session: AsyncSession,
    role_id: int,
    load_users: bool = False
) -> Optional[Role]:
    """
    Получить роль по ID
    """
    query = select(Role).where(Role.id == role_id)
    if load_users:
        query = query.options(selectinload(Role.users))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_by_name(
    session: AsyncSession,
    name: str
) -> Optional[Role]:
    """
    Получить роль по названию
    """
    query = select(Role).where(Role.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all(
    session: AsyncSession,
    load_users: bool = False
) -> List[Role]:
    """
    Получить все роли
    """
    query = select(Role).order_by(Role.id)
    if load_users:
        query = query.options(selectinload(Role.users))
    
    result = await session.execute(query)
    return result.scalars().all()

async def get_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    is_admin: Optional[bool] = None,
    is_superadmin: Optional[bool] = None,
    sort_by: str = "id",
    sort_order: str = "asc"
) -> Tuple[List[Role], int]:
    """
    Получить список ролей с пагинацией
    """
    # Базовый запрос
    query = select(Role).options(selectinload(Role.users))
    count_query = select(func.count()).select_from(Role)
    
    # Поиск
    if search:
        search_filter = or_(
            Role.name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Фильтры
    if is_admin is not None:
        query = query.where(Role.is_admin == is_admin)
        count_query = count_query.where(Role.is_admin == is_admin)
    
    if is_superadmin is not None:
        query = query.where(Role.is_superadmin == is_superadmin)
        count_query = count_query.where(Role.is_superadmin == is_superadmin)
    
    # Сортировка
    if sort_by and hasattr(Role, sort_by):
        column = getattr(Role, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Role.id)
    
    # Пагинация
    query = query.offset(skip).limit(limit)
    
    # Выполнение
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    return items, total

async def get_with_users_count(
    session: AsyncSession,
    role_id: int
) -> Tuple[Optional[Role], int]:
    """
    Получить роль и количество пользователей с этой ролью
    """
    role = await get_by_id(session, role_id, load_users=True)
    if not role:
        return None, 0
    
    users_count = len(role.users) if role.users else 0
    return role, users_count

# ========== ПРОВЕРКА СУЩЕСТВОВАНИЯ ==========

async def check_name_exists(
    session: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None
) -> bool:
    """
    Проверить, существует ли роль с таким именем
    """
    query = select(Role).where(Role.name == name)
    if exclude_id:
        query = query.where(Role.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None

# ========== СОЗДАНИЕ ==========

async def create(
    session: AsyncSession,
    role_create: RoleCreate
) -> Role:
    """
    Создать новую роль
    """
    role = Role(**role_create.dict())
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role

# ========== ОБНОВЛЕНИЕ ==========

async def update(
    session: AsyncSession,
    role_id: int,
    role_update: RoleUpdate
) -> Optional[Role]:
    """
    Обновить роль
    """
    role = await get_by_id(session, role_id)
    if not role:
        return None
    
    # Получаем данные для обновления (только переданные поля)
    update_data = role_update.dict(exclude_unset=True)
    
    # Обновляем поля
    for field, value in update_data.items():
        if hasattr(role, field):
            setattr(role, field, value)
    
    await session.commit()
    await session.refresh(role)
    return role

# ========== УДАЛЕНИЕ ==========

async def delete(
    session: AsyncSession,
    role_id: int
) -> bool:
    """
    Удалить роль (только если нет связанных пользователей)
    """
    role = await get_by_id(session, role_id, load_users=True)
    if not role:
        return False
    
    # Проверяем, есть ли пользователи с этой ролью
    if role.users and len(role.users) > 0:
        raise ValueError(f"Невозможно удалить роль {role.name}: есть связанные пользователи")
    
    await session.delete(role)
    await session.commit()
    return True

# ========== ДОПОЛНИТЕЛЬНЫЕ ОПЕРАЦИИ ==========

async def get_permissions_matrix(
    session: AsyncSession,
    role_id: int
) -> dict:
    """
    Получить матрицу прав для роли в удобном формате
    """
    role = await get_by_id(session, role_id)
    if not role:
        return {}
    
    # Группируем права по категориям
    permissions = {
        "admin_flags": {
            "is_admin": role.is_admin,
            "is_superadmin": role.is_superadmin
        },
        "users": {
            "read": role.user_read,
            "modify": role.user_modify,
            "create": role.user_create,
            "delete": role.user_delete
        },
        "roles": {
            "read": role.role_read,
            "modify": role.role_modify,
            "create": role.role_create,
            "delete": role.role_delete
        },
        "spec_regions": {
            "read": role.spec_region_read,
            "modify": role.spec_region_modify,
            "create": role.spec_region_create,
            "delete": role.spec_region_delete
        },
        "regions": {
            "read": role.region_read,
            "modify": role.region_modify,
            "create": role.region_create,
            "delete": role.region_delete
        },
        
        # ... добавить остальные категории по аналогии
    }
    
    return permissions