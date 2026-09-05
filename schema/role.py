from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class RoleBase(BaseModel):
    """Базовая схема роли — все поля прав. Должна быть в синхроне с `model.role.Role`.

    `RoleCreate` и `RoleUpdate` наследуются от неё (см. ниже), поэтому новое
    разрешение достаточно добавить **только сюда**.
    """
    name: str = Field(..., min_length=2, max_length=50, description="Название роли")

    # Признаки административных ролей
    is_admin: bool = Field(False, description="Административная роль")
    is_superadmin: bool = Field(False, description="Супер-администратор")

    # Права на пользователей
    user_read: bool = Field(False, description="Право на чтение пользователей")
    user_modify: bool = Field(False, description="Право на изменение пользователей")
    user_create: bool = Field(False, description="Право на создание пользователей")
    user_delete: bool = Field(False, description="Право на удаление пользователей")
    user_onboard_mobile: bool = Field(
        False, description="Право выдавать QR/ссылку для входа в мобильное приложение"
    )

    # Права на роли
    role_read: bool = Field(False, description="Право на чтение ролей")
    role_modify: bool = Field(False, description="Право на изменение ролей")
    role_create: bool = Field(False, description="Право на создание ролей")
    role_delete: bool = Field(False, description="Право на удаление ролей")

    # Права на типы регионов
    spec_region_read: bool = Field(False, description="Право на чтение типов регионов")
    spec_region_modify: bool = Field(False, description="Право на изменение типов регионов")
    spec_region_create: bool = Field(False, description="Право на создание типов регионов")
    spec_region_delete: bool = Field(False, description="Право на удаление типов регионов")

    # Права на регионы
    region_read: bool = Field(False, description="Право на чтение регионов")
    region_modify: bool = Field(False, description="Право на изменение регионов")
    region_create: bool = Field(False, description="Право на создание регионов")
    region_delete: bool = Field(False, description="Право на удаление регионов")

    # Права на типы районов
    spec_arial_read: bool = Field(False, description="Право на чтение типов районов")
    spec_arial_modify: bool = Field(False, description="Право на изменение типов районов")
    spec_arial_create: bool = Field(False, description="Право на создание типов районов")
    spec_arial_delete: bool = Field(False, description="Право на удаление типов районов")

    # Права на районы
    arial_read: bool = Field(False, description="Право на чтение районов")
    arial_modify: bool = Field(False, description="Право на изменение районов")
    arial_create: bool = Field(False, description="Право на создание районов")
    arial_delete: bool = Field(False, description="Право на удаление районов")

    # Права на типы нас.пунктов
    spec_locality_read: bool = Field(False, description="Право на чтение типов нас.пунктов")
    spec_locality_modify: bool = Field(False, description="Право на изменение типов нас.пунктов")
    spec_locality_create: bool = Field(False, description="Право на создание типов нас.пунктов")
    spec_locality_delete: bool = Field(False, description="Право на удаление типов нас.пунктов")

    # Права на нас.пункты
    locality_read: bool = Field(False, description="Право на чтение нас.пунктов")
    locality_modify: bool = Field(False, description="Право на изменение нас.пунктов")
    locality_create: bool = Field(False, description="Право на создание нас.пунктов")
    locality_delete: bool = Field(False, description="Право на удаление нас.пунктов")

    # Права на типы улиц
    spec_street_read: bool = Field(False, description="Право на чтение типов улиц")
    spec_street_modify: bool = Field(False, description="Право на изменение типов улиц")
    spec_street_create: bool = Field(False, description="Право на создание типов улиц")
    spec_street_delete: bool = Field(False, description="Право на удаление типов улиц")

    # Права на улицы
    street_read: bool = Field(False, description="Право на чтение улиц")
    street_modify: bool = Field(False, description="Право на изменение улиц")
    street_create: bool = Field(False, description="Право на создание улиц")
    street_delete: bool = Field(False, description="Право на удаление улиц")

    # Права на типы строений
    spec_build_read: bool = Field(False, description="Право на чтение типов строений")
    spec_build_modify: bool = Field(False, description="Право на изменение типов строений")
    spec_build_create: bool = Field(False, description="Право на создание типов строений")
    spec_build_delete: bool = Field(False, description="Право на удаление типов строений")

    # Права на типы помещений
    spec_room_read: bool = Field(False, description="Право на чтение типов помещений")
    spec_room_modify: bool = Field(False, description="Право на изменение типов помещений")
    spec_room_create: bool = Field(False, description="Право на создание типов помещений")
    spec_room_delete: bool = Field(False, description="Право на удаление типов помещений")

    # Права на банки
    bank_read: bool = Field(False, description="Право на чтение банков")
    bank_modify: bool = Field(False, description="Право на изменение банков")
    bank_create: bool = Field(False, description="Право на создание банков")
    bank_delete: bool = Field(False, description="Право на удаление банков")

    # Права на организации
    organization_read: bool = Field(False, description="Право на чтение организаций")
    organization_modify: bool = Field(False, description="Право на изменение организаций")
    organization_create: bool = Field(False, description="Право на создание организаций")
    organization_delete: bool = Field(False, description="Право на удаление организаций")

    # Права на типы контрактов
    spec_contract_read: bool = Field(False, description="Право на чтение типов контрактов")
    spec_contract_modify: bool = Field(False, description="Право на изменение типов контрактов")
    spec_contract_create: bool = Field(False, description="Право на создание типов контрактов")
    spec_contract_delete: bool = Field(False, description="Право на удаление типов контрактов")

    # Права на контракты
    contract_read: bool = Field(False, description="Право на чтение контрактов")
    contract_modify: bool = Field(False, description="Право на изменение контрактов")
    contract_create: bool = Field(False, description="Право на создание контрактов")
    contract_delete: bool = Field(False, description="Право на удаление контрактов")

    # Права на дополнительные соглашения
    sub_contract_read: bool = Field(False, description="Право на чтение доп. соглашений")
    sub_contract_modify: bool = Field(False, description="Право на изменение доп. соглашений")
    sub_contract_create: bool = Field(False, description="Право на создание доп. соглашений")
    sub_contract_delete: bool = Field(False, description="Право на удаление доп. соглашений")

    # Права на периоды
    period_read: bool = Field(False, description="Право на чтение периодов")
    period_modify: bool = Field(False, description="Право на изменение периодов")
    period_create: bool = Field(False, description="Право на создание периодов")
    period_delete: bool = Field(False, description="Право на удаление периодов")

    # Права на типы оборудования
    spec_equipment_read: bool = Field(False, description="Право на чтение типов оборудования")
    spec_equipment_modify: bool = Field(False, description="Право на изменение типов оборудования")
    spec_equipment_create: bool = Field(False, description="Право на создание типов оборудования")
    spec_equipment_delete: bool = Field(False, description="Право на удаление типов оборудования")

    # Права на оборудование
    equipment_read: bool = Field(False, description="Право на чтение оборудования")
    equipment_modify: bool = Field(False, description="Право на изменение оборудования")
    equipment_create: bool = Field(False, description="Право на создание оборудования")
    equipment_delete: bool = Field(False, description="Право на удаление оборудования")

    # Права на объекты
    object_read: bool = Field(False, description="Право на чтение объектов")
    object_modify: bool = Field(False, description="Право на изменение объектов")
    object_create: bool = Field(False, description="Право на создание объектов")
    object_delete: bool = Field(False, description="Право на удаление объектов")

    # Права на оборудование на объектах
    object_equipment_read: bool = Field(False, description="Право на чтение оборудования на объектах")
    object_equipment_modify: bool = Field(False, description="Право на изменение оборудования на объектах")
    object_equipment_create: bool = Field(False, description="Право на создание оборудования на объектах")
    object_equipment_delete: bool = Field(False, description="Право на удаление оборудования на объектах")

    # Права на операции для оборудования
    operation_read: bool = Field(False, description="Право на чтение операций для оборудования")
    operation_modify: bool = Field(False, description="Право на изменение операций для оборудования")
    operation_create: bool = Field(False, description="Право на создание операций для оборудования")
    operation_delete: bool = Field(False, description="Право на удаление операций для оборудования")

    # Права на должности руководителей для контрактов
    spec_job_title_read: bool = Field(False, description="Право на чтение должностей руководителей")
    spec_job_title_modify: bool = Field(False, description="Право на изменение должностей руководителей")
    spec_job_title_create: bool = Field(False, description="Право на создание должностей руководителей")
    spec_job_title_delete: bool = Field(False, description="Право на удаление должностей руководителей")

    # Права на типы заявок
    spec_order_read: bool = Field(False, description="Право на чтение типов заявок")
    spec_order_modify: bool = Field(False, description="Право на изменение типов заявок")
    spec_order_create: bool = Field(False, description="Право на создание типов заявок")
    spec_order_delete: bool = Field(False, description="Право на удаление типов заявок")

    # Права на типы обслуживаемых систем
    spec_system_read: bool = Field(False, description="Право на чтение типов обслуживаемых систем")
    spec_system_modify: bool = Field(False, description="Право на изменение типов обслуживаемых систем")
    spec_system_create: bool = Field(False, description="Право на создание типов обслуживаемых систем")
    spec_system_delete: bool = Field(False, description="Право на удаление типов обслуживаемых систем")

    # Права на заявки
    order_read: bool = Field(False, description="Право на чтение заявок")
    order_modify: bool = Field(False, description="Право на изменение заявок")
    order_create: bool = Field(False, description="Право на создание заявок")
    order_delete: bool = Field(False, description="Право на удаление заявок")

    # Права на отчёты
    report_read: bool = Field(False, description="Право на чтение отчётов")
    report_modify: bool = Field(False, description="Право на изменение отчётов")
    report_create: bool = Field(False, description="Право на создание отчётов")
    report_delete: bool = Field(False, description="Право на удаление отчётов")

    # Права на неисправности
    issue_read: bool = Field(False, description="Право на чтение неисправностей")
    issue_modify: bool = Field(False, description="Право на изменение неисправностей")
    issue_create: bool = Field(False, description="Право на создание неисправностей")
    issue_delete: bool = Field(False, description="Право на удаление неисправностей")

    # Права на статусы неисправностей (справочник)
    spec_status_read: bool = Field(False, description="Право на чтение статусов неисправностей")
    spec_status_modify: bool = Field(False, description="Право на изменение статусов неисправностей")
    spec_status_create: bool = Field(False, description="Право на создание статусов неисправностей")
    spec_status_delete: bool = Field(False, description="Право на удаление статусов неисправностей")

    # Права на статусы заявок (справочник)
    spec_order_status_read: bool = Field(False, description="Право на чтение статусов заявок")
    spec_order_status_modify: bool = Field(False, description="Право на изменение статусов заявок")
    spec_order_status_create: bool = Field(False, description="Право на создание статусов заявок")
    spec_order_status_delete: bool = Field(False, description="Право на удаление статусов заявок")

    # Права на статусы отчётов (справочник)
    spec_report_status_read: bool = Field(False, description="Право на чтение статусов отчётов")
    spec_report_status_modify: bool = Field(False, description="Право на изменение статусов отчётов")
    spec_report_status_create: bool = Field(False, description="Право на создание статусов отчётов")
    spec_report_status_delete: bool = Field(False, description="Право на удаление статусов отчётов")

    # Права на приоритеты неисправностей (справочник)
    spec_priority_read: bool = Field(False, description="Право на чтение приоритетов неисправностей")
    spec_priority_modify: bool = Field(False, description="Право на изменение приоритетов неисправностей")
    spec_priority_create: bool = Field(False, description="Право на создание приоритетов неисправностей")
    spec_priority_delete: bool = Field(False, description="Право на удаление приоритетов неисправностей")

    # Права на типы журналов (бланки для объектов)
    spec_journal_read: bool = Field(False, description="Право на чтение типов журналов")
    spec_journal_modify: bool = Field(False, description="Право на изменение типов журналов")
    spec_journal_create: bool = Field(False, description="Право на создание типов журналов")
    spec_journal_delete: bool = Field(False, description="Право на удаление типов журналов")

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(RoleBase):
    """Схема создания роли — наследует все поля прав."""
    description: Optional[str] = Field(None, max_length=1000, description="Описание/комментарий")


class RoleUpdate(RoleBase):
    """Схема обновления роли — наследует все поля прав.

    `data.role.update_role` использует `model_dump(exclude_unset=True)`,
    поэтому в PUT-запрос можно передавать только меняемые поля.
    """
    description: Optional[str] = Field(None, max_length=1000)


class RoleResponse(RoleBase):
    id: int
    is_protected: bool = False
    description: Optional[str] = None
    users_count: Optional[int] = Field(0, description="Количество пользователей с этой ролью")

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    id: int
    name: str
    is_admin: bool
    is_superadmin: bool
    is_protected: bool = False
    description: Optional[str] = None
    users_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class RoleSimpleResponse(BaseModel):
    id: int
    name: str
    is_admin: bool
    is_superadmin: bool
    is_protected: bool = False

    model_config = ConfigDict(from_attributes=True)
