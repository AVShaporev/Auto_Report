"""
Bootstrap script: создаёт роль `superadmin` со всеми правами и одного юзера-суперадмина.

Запускается один раз на пустой БД (или повторно для добавления юзеров под существующей ролью).

Использование:
    ADMIN_NAME=admin ADMIN_PASSWORD='<strong>' \\
    poetry run python bootstrap_admin.py

Опциональные переменные:
    ADMIN_FULL_NAME, ADMIN_EMAIL, ADMIN_PHONE, ADMIN_TELEGRAM_ID
"""
import asyncio
import os
import sys

from sqlalchemy import Boolean, select
from sqlalchemy.inspection import inspect

from database.database import new_session
from model.role import Role
from model.user import User
from service.auth import get_password_hash


SUPERADMIN_ROLE_NAME = "superadmin"


def _all_role_perm_flags() -> dict:
    """Возвращает True для всех Boolean-колонок Role (is_admin, is_superadmin, *_read/create/modify/delete)."""
    columns = inspect(Role).columns
    return {col.name: True for col in columns if isinstance(col.type, Boolean)}


async def main() -> int:
    name = os.environ.get("ADMIN_NAME")
    password = os.environ.get("ADMIN_PASSWORD")
    if not name or not password:
        print("ERROR: set ADMIN_NAME and ADMIN_PASSWORD env vars", file=sys.stderr)
        return 2

    full_name = os.environ.get("ADMIN_FULL_NAME") or name
    email = os.environ.get("ADMIN_EMAIL")
    phone = os.environ.get("ADMIN_PHONE")
    telegram_id = os.environ.get("ADMIN_TELEGRAM_ID")

    async with new_session() as session:
        role = (await session.execute(
            select(Role).where(Role.name == SUPERADMIN_ROLE_NAME)
        )).scalar_one_or_none()

        if role is None:
            role = Role(name=SUPERADMIN_ROLE_NAME, **_all_role_perm_flags())
            session.add(role)
            await session.flush()
            print(f"Created role '{SUPERADMIN_ROLE_NAME}' (id={role.id}) with all permissions")
        else:
            print(f"Role '{SUPERADMIN_ROLE_NAME}' (id={role.id}) already exists, reusing")

        existing_user = (await session.execute(
            select(User).where(User.name == name)
        )).scalar_one_or_none()
        if existing_user is not None:
            print(f"ERROR: user '{name}' already exists (id={existing_user.id})", file=sys.stderr)
            return 1

        user = User(
            name=name,
            full_name=full_name,
            hash=get_password_hash(password),
            email=email,
            phone=phone,
            telegram_id=telegram_id,
            role_id=role.id,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"Created superadmin user '{user.name}' (id={user.id})")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
