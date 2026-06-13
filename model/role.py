from typing import List

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from database.database import Base, int_pk, str_uniq, str_null_true


class Role(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]

    # признак админитративной роли
    is_admin: Mapped[bool] = mapped_column(default=False)
    is_superadmin: Mapped[bool] = mapped_column(default=False)

    # Защита от удаления/изменения через UI (bootstrap-роль superadmin).
    is_protected: Mapped[bool] = mapped_column(default=False, server_default='false')

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

    # права на типы регионов
    spec_region_read: Mapped[bool] = mapped_column(default=False)
    spec_region_modify: Mapped[bool] = mapped_column(default=False)
    spec_region_create: Mapped[bool] = mapped_column(default=False)
    spec_region_delete: Mapped[bool] = mapped_column(default=False)

    # права на регионы
    region_read: Mapped[bool] = mapped_column(default=False)
    region_modify: Mapped[bool] = mapped_column(default=False)
    region_create: Mapped[bool] = mapped_column(default=False)
    region_delete: Mapped[bool] = mapped_column(default=False)

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

    # права на типы нас.пунктов
    spec_locality_read: Mapped[bool] = mapped_column(default=False)
    spec_locality_modify: Mapped[bool] = mapped_column(default=False)
    spec_locality_create: Mapped[bool] = mapped_column(default=False)
    spec_locality_delete: Mapped[bool] = mapped_column(default=False)

    # права на нас.пункты
    locality_read: Mapped[bool] = mapped_column(default=False)
    locality_modify: Mapped[bool] = mapped_column(default=False)
    locality_create: Mapped[bool] = mapped_column(default=False)
    locality_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы улиц
    spec_street_read: Mapped[bool] = mapped_column(default=False)
    spec_street_modify: Mapped[bool] = mapped_column(default=False)
    spec_street_create: Mapped[bool] = mapped_column(default=False)
    spec_street_delete: Mapped[bool] = mapped_column(default=False)

    # права на улицы
    street_read: Mapped[bool] = mapped_column(default=False)
    street_modify: Mapped[bool] = mapped_column(default=False)
    street_create: Mapped[bool] = mapped_column(default=False)
    street_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы строений
    spec_build_read: Mapped[bool] = mapped_column(default=False)
    spec_build_modify: Mapped[bool] = mapped_column(default=False)
    spec_build_create: Mapped[bool] = mapped_column(default=False)
    spec_build_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы помещений
    spec_room_read: Mapped[bool] = mapped_column(default=False)
    spec_room_modify: Mapped[bool] = mapped_column(default=False)
    spec_room_create: Mapped[bool] = mapped_column(default=False)
    spec_room_delete: Mapped[bool] = mapped_column(default=False)

    # права на банки
    bank_read: Mapped[bool] = mapped_column(default=False)
    bank_modify: Mapped[bool] = mapped_column(default=False)
    bank_create: Mapped[bool] = mapped_column(default=False)
    bank_delete: Mapped[bool] = mapped_column(default=False)

    # права на организации
    organization_read: Mapped[bool] = mapped_column(default=False)
    organization_modify: Mapped[bool] = mapped_column(default=False)
    organization_create: Mapped[bool] = mapped_column(default=False)
    organization_delete: Mapped[bool] = mapped_column(default=False)

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

    # права на дополнительные соглашения
    sub_contract_read: Mapped[bool] = mapped_column(default=False)
    sub_contract_create: Mapped[bool] = mapped_column(default=False)
    sub_contract_modify: Mapped[bool] = mapped_column(default=False)
    sub_contract_delete: Mapped[bool] = mapped_column(default=False)

    # права на периоды
    period_read: Mapped[bool] = mapped_column(default=False)
    period_modify: Mapped[bool] = mapped_column(default=False)
    period_create: Mapped[bool] = mapped_column(default=False)
    period_delete: Mapped[bool] = mapped_column(default=False)

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

    # права на объекты
    object_read: Mapped[bool] = mapped_column(default=False)
    object_modify: Mapped[bool] = mapped_column(default=False)
    object_create: Mapped[bool] = mapped_column(default=False)
    object_delete: Mapped[bool] = mapped_column(default=False)

    # права на оборудование на объектах
    object_equipment_read: Mapped[bool] = mapped_column(default=False)
    object_equipment_modify: Mapped[bool] = mapped_column(default=False)
    object_equipment_create: Mapped[bool] = mapped_column(default=False)
    object_equipment_delete: Mapped[bool] = mapped_column(default=False)

    # права на операции для оборудования
    operation_read: Mapped[bool] = mapped_column(default=False)
    operation_modify: Mapped[bool] = mapped_column(default=False)
    operation_create: Mapped[bool] = mapped_column(default=False)
    operation_delete: Mapped[bool] = mapped_column(default=False)

    # права на должности руководителей
    spec_job_title_read: Mapped[bool] = mapped_column(default=False)
    spec_job_title_modify: Mapped[bool] = mapped_column(default=False)
    spec_job_title_create: Mapped[bool] = mapped_column(default=False)
    spec_job_title_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы заявок
    spec_order_read: Mapped[bool] = mapped_column(default=False)
    spec_order_create: Mapped[bool] = mapped_column(default=False)
    spec_order_modify: Mapped[bool] = mapped_column(default=False)
    spec_order_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы обслуживаемых систем
    spec_system_read: Mapped[bool] = mapped_column(default=False)
    spec_system_create: Mapped[bool] = mapped_column(default=False)
    spec_system_modify: Mapped[bool] = mapped_column(default=False)
    spec_system_delete: Mapped[bool] = mapped_column(default=False)

    # права на заявки
    order_read: Mapped[bool] = mapped_column(default=False)
    order_create: Mapped[bool] = mapped_column(default=False)
    order_modify: Mapped[bool] = mapped_column(default=False)
    order_delete: Mapped[bool] = mapped_column(default=False)

    # права на отчёты
    report_read: Mapped[bool] = mapped_column(default=False)
    report_create: Mapped[bool] = mapped_column(default=False)
    report_modify: Mapped[bool] = mapped_column(default=False)
    report_delete: Mapped[bool] = mapped_column(default=False)

    # права на неисправности
    issue_read: Mapped[bool] = mapped_column(default=False)
    issue_create: Mapped[bool] = mapped_column(default=False)
    issue_modify: Mapped[bool] = mapped_column(default=False)
    issue_delete: Mapped[bool] = mapped_column(default=False)

    # права на статусы неисправностей (справочник)
    spec_status_read: Mapped[bool] = mapped_column(default=False)
    spec_status_create: Mapped[bool] = mapped_column(default=False)
    spec_status_modify: Mapped[bool] = mapped_column(default=False)
    spec_status_delete: Mapped[bool] = mapped_column(default=False)

    # права на приоритеты неисправностей (справочник)
    spec_priority_read: Mapped[bool] = mapped_column(default=False)
    spec_priority_create: Mapped[bool] = mapped_column(default=False)
    spec_priority_modify: Mapped[bool] = mapped_column(default=False)
    spec_priority_delete: Mapped[bool] = mapped_column(default=False)

    # права на типы журналов
    spec_journal_read: Mapped[bool] = mapped_column(default=False)
    spec_journal_create: Mapped[bool] = mapped_column(default=False)
    spec_journal_modify: Mapped[bool] = mapped_column(default=False)
    spec_journal_delete: Mapped[bool] = mapped_column(default=False)
            
    # Определяем отношения: одна роль может принаддлежать нескольким пользователям
    # lazy="select" (default) — НЕ грузим автоматически. data/role.py явно
    # использует .options(selectinload(Role.users)) там, где это нужно
    # (списки ролей, удаление с проверкой назначенных юзеров).
    users: Mapped[List["User"]] = relationship(
                                                    "User",
                                                    back_populates="role"
                                                )

    def __repr__(self):
        return f"Role(id={self.id}, name={self.name})"