from pydantic import BaseModel, Field, ConfigDict


class SpecOrderStatusOptionResponse(BaseModel):
    """Статус заявки для селектов/бейджей на фронтах.

    code — системный код на Order.status ('new', 'in_progress', ...).
    name — ру-имя ('Новая', 'В работе', ...).
    display_order — рекомендуемый порядок в UI.
    """
    id: int
    code: str
    name: str
    is_system: bool = False
    display_order: int = 0

    model_config = ConfigDict(from_attributes=True)
