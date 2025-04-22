from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


class Role(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]

    # права на пользователей
    user_read: Mapped[bool] = mapped_column(default=False)
    user_modify: Mapped[bool] = mapped_column(default=False)
    user_create: Mapped[bool] = mapped_column(default=False)
    user_delete: Mapped[bool] = mapped_column(default=False)

    # права на роли
    role_read: Mapped[bool] = mapped_column(default=False)
    role_modify: Mapped[bool] = mapped_column(default=False)
    role_create: Mapped[bool] = mapped_column(default=False)
    role_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы районов
    spec_arial_read: Mapped[bool] = mapped_column(default=False)
    spec_arial_modify: Mapped[bool] = mapped_column(default=False)
    spec_arial_create: Mapped[bool] = mapped_column(default=False)
    spec_arial_delete: Mapped[bool] = mapped_column(default=False)

    # права на районы
    arial_read: Mapped[bool] = mapped_column(default=False)
    arial_modify: Mapped[bool] = mapped_column(default=False)
    arial_create: Mapped[bool] = mapped_column(default=False)
    arial_delete: Mapped[bool] = mapped_column(default=False)


    # права на банки
    bank_read: Mapped[bool] = mapped_column(default=False)
    bank_modify: Mapped[bool] = mapped_column(default=False)
    bank_create: Mapped[bool] = mapped_column(default=False)
    bank_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы контрактов
    spec_contract_read: Mapped[bool] = mapped_column(default=False)
    spec_contract_modify: Mapped[bool] = mapped_column(default=False)
    spec_contract_create: Mapped[bool] = mapped_column(default=False)
    spec_contract_delete: Mapped[bool] = mapped_column(default=False)

    # права на контракты
    contract_read: Mapped[bool] = mapped_column(default=False)
    contract_modify: Mapped[bool] = mapped_column(default=False)
    contract_create: Mapped[bool] = mapped_column(default=False)
    contract_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы строений
    spec_build_read: Mapped[bool] = mapped_column(default=False)
    spec_build_modify: Mapped[bool] = mapped_column(default=False)
    spec_build_create: Mapped[bool] = mapped_column(default=False)
    spec_build_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы оборудования
    spec_equipment_read: Mapped[bool] = mapped_column(default=False)
    spec_equipment_modify: Mapped[bool] = mapped_column(default=False)
    spec_equipment_create: Mapped[bool] = mapped_column(default=False)
    spec_equipment_delete: Mapped[bool] = mapped_column(default=False)

    # права на оборудование
    equipment_read: Mapped[bool] = mapped_column(default=False)
    equipment_modify: Mapped[bool] = mapped_column(default=False)
    equipment_create: Mapped[bool] = mapped_column(default=False)
    equipment_delete: Mapped[bool] = mapped_column(default=False)
    
        
    # Определяем отношения: одна роль может принаддлежать нескольким пользователям
    users: Mapped[list["User"]] = relationship("User", back_populates="role")