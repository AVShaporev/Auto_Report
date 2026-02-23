from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from model.user import User
from model.role import Role
from schema.role import RoleCreate, RoleUpdate, RoleResponse, RoleListResponse
from schema.pagination import PaginationParams, PaginatedResponse
from service import role as role_service
from core.dependencies import (
    get_current_active_user,
    require_role_read,
    require_role_create,
    require_role_modify,
    require_role_delete
)

router = APIRouter(prefix="/api/role", tags=["role"])

@router.get("/list", response_model=PaginatedResponse[RoleResponse])
async def get_role_list(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    is_admin: Optional[bool] = Query(None, description="Только административные роли"),
    is_superadmin: Optional[bool] = Query(None, description="Только суперадмины"),
    sort_by: str = Query("id", description="Поле сортировки"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    # 👇 Проверка права на чтение
    current_user: User = Depends(require_role_read())
):
    """
    Получить список ролей с пагинацией
    Требуется право role_read
    """
    roles, total = await role_service.get_roles_paginated(
        pagination=pagination,
        search=search,
        is_admin=is_admin,
        is_superadmin=is_superadmin,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Формируем ответ
    role_responses = []
    for role in roles:
        role_dict = {
            "id": role.id,
            "name": role.name,
            "is_admin": role.is_admin,
            "is_superadmin": role.is_superadmin,
            "users_count": len(role.users) if role.users else 0
        }
        
        # Добавляем все права
        for field in dir(role):
            if not field.startswith('_') and field not in ['id', 'name', 'users', 'metadata']:
                if isinstance(getattr(role, field, None), bool):
                    role_dict[field] = getattr(role, field)
        
        role_responses.append(role_dict)
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=role_responses,
        total=total,
        page=pagination.page,
        per_page=pagination.limit,
        pages=pages
    )

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role_by_id(
    role_id: int,
    # 👇 Проверка права на чтение
    current_user: User = Depends(require_role_read())
):
    """
    Получить роль по ID
    Требуется право role_read
    """
    role = await role_service.get_role_by_id(role_id, load_users=True)
    if not role:
        raise HTTPException(status_code=404, detail=f"Роль с id {role_id} не найдена")
    
    # Формируем ответ
    role_dict = {"id": role.id, "name": role.name}
    
    for field in dir(role):
        if not field.startswith('_') and field not in ['id', 'name', 'users', 'metadata']:
            if isinstance(getattr(role, field, None), bool):
                role_dict[field] = getattr(role, field)
    
    role_dict["users_count"] = len(role.users) if role.users else 0
    
    return role_dict

@router.post("/create", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    # 👇 Проверка права на создание
    current_user: User = Depends(require_role_create())
):
    """
    Создать новую роль
    Требуется право role_create
    """
    # Дополнительная проверка: суперадмин может создать только админ
    if role_data.is_superadmin and not current_user.role.is_superadmin:
        raise HTTPException(
            status_code=403, 
            detail="Только суперадминистратор может создавать роли с правами суперадмина"
        )
    
    role = await role_service.create_role(role_data)
    
    # Формируем ответ
    role_dict = {"id": role.id, "name": role.name}
    for field in dir(role):
        if not field.startswith('_') and field not in ['id', 'name', 'users', 'metadata']:
            if isinstance(getattr(role, field, None), bool):
                role_dict[field] = getattr(role, field)
    
    role_dict["users_count"] = 0
    
    return role_dict

@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    # 👇 Проверка права на изменение
    current_user: User = Depends(require_role_modify())
):
    """
    Обновить роль
    Требуется право role_modify
    """
    # Проверяем существование роли
    existing_role = await role_service.get_role_by_id(role_id)
    if not existing_role:
        raise HTTPException(status_code=404, detail=f"Роль с id {role_id} не найдена")
    
    # Защита от изменения суперадмина обычными админами
    if existing_role.is_superadmin and not current_user.role.is_superadmin:
        raise HTTPException(
            status_code=403, 
            detail="Только суперадминистратор может изменять роль суперадмина"
        )
    
    # Если пытаются установить is_superadmin=true, проверяем права
    if role_data.is_superadmin and not current_user.role.is_superadmin:
        raise HTTPException(
            status_code=403, 
            detail="Только суперадминистратор может устанавливать права суперадмина"
        )
    
    role = await role_service.update_role(role_id, role_data)
    
    # Формируем ответ
    role_dict = {"id": role.id, "name": role.name}
    for field in dir(role):
        if not field.startswith('_') and field not in ['id', 'name', 'users', 'metadata']:
            if isinstance(getattr(role, field, None), bool):
                role_dict[field] = getattr(role, field)
    
    # Получаем количество пользователей
    role_with_users = await role_service.get_role_by_id(role_id, load_users=True)
    role_dict["users_count"] = len(role_with_users.users) if role_with_users and role_with_users.users else 0
    
    return role_dict

@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    # 👇 Проверка права на удаление
    current_user: User = Depends(require_role_delete())
):
    """
    Удалить роль
    Требуется право role_delete
    """
    # Проверяем существование роли
    role = await role_service.get_role_by_id(role_id, load_users=True)
    if not role:
        raise HTTPException(status_code=404, detail=f"Роль с id {role_id} не найдена")
    
    # Защита от удаления суперадмина
    if role.is_superadmin:
        raise HTTPException(
            status_code=400, 
            detail="Нельзя удалить роль суперадминистратора"
        )
    
    # Проверка, есть ли пользователи с этой ролью
    if role.users and len(role.users) > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Нельзя удалить роль '{role.name}', так как она назначена {len(role.users)} пользователям"
        )
    
    success = await role_service.delete_role(role_id)
    
    return {
        "status": "success", 
        "message": f"Роль '{role.name}' (id: {role_id}) успешно удалена"
    }