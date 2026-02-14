from fastapi import Depends
from sqlalchemy import select, update, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from model.role import Role
from schema.role import RoleResponse

from database.database import new_session
# from database.database import get_async_session

# функция определения состояния объекта SQ:Alchemy
def check_object_state(obj):
    inspector = inspect(obj)
    print(f"Object: {obj}")
    print(f"Persistent: {inspector.persistent}")
    print(f"Detached: {inspector.detached}")
    print(f"Transient: {inspector.transient}")
    print(f"Pending: {inspector.pending}")
    print(f"Session: {inspector.session}")


# Функция перевода из строки в модель
def row_to_model(row: tuple) -> Role:
    name, userrole, = row
    return create(name=name,
                    )

# Функция из модели в строку
def model_to_dict(role: Role) -> dict:
    return report.dict()

# Функция запроса из БД всех строк
async def get_all():
    async with new_session() as session:
        roles = None
        query = select(Role)
        res = await session.execute(query)
        roles = res.scalars().all()
        # roles = [user for user in users if user.name != 'superadmin']
    return roles

# Функция запроса из БД одну строку по имени объекта
async def get_one_by_name(name: str) -> Role:
    async with new_session() as session:
        query = select(Role).filter(Role.name == name)
        res = await session.execute(query)
        role = res.scalars().one_or_none()
        return role

# Функция запроса из БД одну строку по id объекта
async def get_one_by_id(id: int) -> Role:
    async with new_session() as session:
        query = select(Role).filter(Role.id == id)
        res = await session.execute(query)
        role = res.scalars().one_or_none()
        return role

# Функция добавления строки в БД
async def create(role: Role) -> Role:
    async with new_session() as session:
        session.add(role)
        await session.flush()
        await session.commit()
        role = await get_one_by_name(role.name)
        return role

# Функция изменения строки
async def modify(
                role_id: int,  # Явно указываем, что это ID
                role_update: RoleResponse
                # session: AsyncSession = Depends(new_session)    # Передаем сессию, не создаем внутри
                ) -> Role:
    """
    Обновляет роль по ID
    
    Args:
        role_id: ID роли для обновления
        role_update: Данные для обновления
        session: Асинхронная сессия SQLAlchemy
    
    Returns:
        Обновленная роль
    
    Raises:
        HTTPException: если роль не найдена или имя не уникально
    """
    async with new_session() as session:

        # async with new_session() as session:
        # 1. Ищем роль по ID
        query = select(Role).where(Role.id == role_id)
        res = await session.execute(query)
        role = res.scalar_one_or_none()
        
        # 2. Проверяем существование
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with id {role_id} not found"
            )

        # 3. Получаем данные для обновления
        update_data = role_update.dict()
        
        # 4. Специальные проверки
        if "name" in update_data and update_data["name"] != role.name:
            # Проверяем уникальность имени
            name_check = await session.execute(
                select(Role).where(
                    Role.name == update_data["name"],
                    Role.id != role_id
                )
            )
            if name_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Такое имя роли уже сущестует!!!"
                )
        
        # 5. Обновляем поля
        for field, value in update_data.items():
            setattr(role, field, value)
        
        # 6. Сохраняем
        await session.commit()
        await session.refresh(role)
        
        return role

# Функция удаления из БД строки поимени
async def delete_by_name(name: str) -> bool:
    role = await get_one_by_name(name)
    async with new_session() as session:
        await session.delete(role)
        await session.commit()
        return True

async def delete_by_id(id: int) -> bool:
    role = await get_one_by_id(id)
    async with new_session() as session:
        await session.delete(role)
        await session.commit()
        return True