from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SpecOrderStatusOptionResponse(BaseModel):
    """Статус заявки для селектов/фильтров/бейджей на фронтах.

    Канон 4 поля: id, name, description, is_default. Ру-имя — единственный
    источник отображения; на фронтах никакого code→name маппинга нет.
    """
    id: int
    name: str
    description: Optional[str] = None
    is_default: bool = False

    model_config = ConfigDict(from_attributes=True)
