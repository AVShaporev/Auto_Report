from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar, List

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Параметры пагинации из query string"""
    page: int = Field(1, ge=1, description="Номер страницы")
    per_page: int = Field(20, ge=1, le=100, description="Элементов на странице")

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page

class PaginatedResponse(BaseModel, Generic[T]):
    """Универсальный ответ с пагинацией"""
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int