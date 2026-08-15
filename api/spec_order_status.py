from typing import List

from fastapi import APIRouter, Depends

from model.user import User
from schema.spec_order_status import SpecOrderStatusOptionResponse
from data import spec_order_status as spec_order_status_data
from core.dependencies import get_current_active_user
from database.database import new_session


# Read-only справочник статусов заявки на ТО. Все строки — is_system=True,
# сидится миграцией e8f9a0b1c2d3. CRUD не требуется: коды жёстко зашиты
# в Literal-валидаторе update_order_status (api/order.py). Endpoint нужен
# только чтобы фронты (web + mobile) тянули отсюда ру-имена и порядок
# в селектах, не хардкодя.
router = APIRouter(prefix="/api/spec_order_status", tags=["spec_order_status"])


@router.get("/options", response_model=List[SpecOrderStatusOptionResponse])
async def get_spec_order_status_options(
    current_user: User = Depends(get_current_active_user),
):
    """Список статусов заявок в порядке display_order.

    Требует только аутентификацию — справочник публичный (в рамках тенанта).
    """
    async with new_session() as session:
        rows = await spec_order_status_data.get_spec_order_status_all(session)
        return rows
