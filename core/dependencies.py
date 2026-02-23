from fastapi import Depends, HTTPException, status
from model.user import User
from service.auth import get_current_user  # 👈 Ваша функция отсюда

# Базовые зависимости для получения пользователя
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Проверка, что пользователь активен
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован"
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )
    
    return current_user

# Фабрики для проверки прав на роли
def require_role_read():
    """
    Зависимость для проверки права на чтение ролей
    """
    async def dependency(current_user: User = Depends(get_current_active_user)):
        if not current_user.role.role_read:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для просмотра ролей"
            )
        return current_user
    return dependency

def require_role_create():
    """
    Зависимость для проверки права на создание ролей
    """
    async def dependency(current_user: User = Depends(get_current_active_user)):
        if not current_user.role.role_create:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для создания ролей"
            )
        return current_user
    return dependency

def require_role_modify():
    """
    Зависимость для проверки права на изменение ролей
    """
    async def dependency(current_user: User = Depends(get_current_active_user)):
        if not current_user.role.role_modify:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для изменения ролей"
            )
        return current_user
    return dependency

def require_role_delete():
    """
    Зависимость для проверки права на удаление ролей
    """
    async def dependency(current_user: User = Depends(get_current_active_user)):
        if not current_user.role.role_delete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для удаления ролей"
            )
        return current_user
    return dependency

# Универсальная зависимость для проверки нескольких прав
def require_any_role_permission(permissions: list):
    """
    Проверка наличия хотя бы одного права из списка
    """
    async def dependency(current_user: User = Depends(get_current_active_user)):
        user_permissions = []
        
        for perm in permissions:
            if hasattr(current_user.role, perm) and getattr(current_user.role, perm):
                user_permissions.append(perm)
        
        if not user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав. Требуется одно из: {permissions}"
            )
        return current_user
    return dependency