"""ActivityLog — журнал пользовательских действий (Auto_Report v1.0.14).

Замена LogsView в тенанте. Технические логи (JSONL) переезжают в
admin.cool-doc.ru отдельной фазой (см. task #312).
"""
from typing import Any, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base, int_pk


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int_pk]
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    # Снапшот имени: сохраняется даже если user_id обнулился при удалении.
    user_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # 'create' | 'update' | 'delete' | 'change_status' | 'login' | 'logout'
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # 'order' | 'report' | 'issue' | 'user' | 'role' | 'contract' | 'object' | ...
    entity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # id сущности; для delete может быть None если id уже потеряли
    entity_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    # Человекочитаемый русский текст, напр. «Создал заявку №2026-001»
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    # Доп. данные — before/after diff, params запроса, любой контекст
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # created_at + updated_at приходят из Base (server_default=now()).

    user = relationship("User", foreign_keys=[user_id], lazy="raise")
