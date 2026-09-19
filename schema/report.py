from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, List
from datetime import date, datetime

# ========== БАЗОВЫЕ СХЕМЫ ==========

class ReportBase(BaseModel):
    """Базовая схема отчета (без user_id для входящих данных)"""
    number: str = Field(..., min_length=1, max_length=500, description="Номер отчета")
    period_id: int = Field(..., ge=1, description="ID периода")
    contract_id: int = Field(..., ge=1, description="ID контракта")
    object_id: int = Field(..., ge=1, description="ID объекта")
    description: Optional[str] = Field(None, max_length=1000, description="Описание отчета")
    
    model_config = ConfigDict(from_attributes=True)


# ========== ПОДПИСЬ ПРЕДСТАВИТЕЛЯ ЗАКАЗЧИКА (узор, ПЭП) ==========

class SignatureOffline(BaseModel):
    """Подпись, поставленная без сети: узор зашифрован открытым ключом
    организации (GET /api/signature/public-key), проверка — на сервере."""
    representative_id: int = Field(..., ge=1)
    encrypted: str = Field(..., min_length=16, max_length=4096, description="base64 RSA-OAEP(SHA-256)")
    signed_at: Optional[datetime] = None


# ========== СХЕМЫ ДЛЯ СОЗДАНИЯ ==========

class ReportCreate(BaseModel):
    """Схема для создания отчета (без user_id).

    Номер генерируется сервером по маске
    "{object_id}/{MM}/{YYYY}/{customer.short_name}/{contract.short_subject}"
    из переданного report_period (формат "YYYY-MM").

    period_id / contract_id / object_id опциональны: если не переданы,
    бэк вытащит их из выбранной заявки (order.object.period_id,
    order.contract_id, order.object_id). Если переданы — должны совпадать
    с тем, что лежит на заявке.
    """
    order_id: int = Field(..., ge=1, description="ID заявки (связь 1:1)")
    period_id: Optional[int] = Field(None, ge=1, description="ID периода (опц., возьмётся из заявки)")
    contract_id: Optional[int] = Field(None, ge=1, description="ID контракта (опц., возьмётся из заявки)")
    object_id: Optional[int] = Field(None, ge=1, description="ID объекта (опц., возьмётся из заявки)")
    description: Optional[str] = Field(None, max_length=1000, description="Описание отчета")
    report_period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
                               description="Отчётный период в формате YYYY-MM")
    # Подпись представителя заказчика: онлайн — токен из POST
    # /api/signature/verify, офлайн — зашифрованный узор.
    signature_token: Optional[str] = Field(None, max_length=2000)
    signature_offline: Optional[SignatureOffline] = None

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ ==========

class ReportUpdate(BaseModel):
    """Схема для обновления отчета (все поля опциональны)"""
    number: Optional[str] = Field(None, min_length=1, max_length=500)
    period_id: Optional[int] = Field(None, ge=1)
    contract_id: Optional[int] = Field(None, ge=1)
    object_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=1000)
    # Подпись: токен или офлайн-узор — поставить/заменить; clear_signature —
    # убрать. До утверждения отчёта.
    signature_token: Optional[str] = Field(None, max_length=2000)
    signature_offline: Optional[SignatureOffline] = None
    clear_signature: bool = False

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ СМЕНЫ СТАТУСА ==========

class ReportStatusUpdate(BaseModel):
    """Схема для смены статуса отчёта (FK на spec_report_statuses)."""
    status_id: int = Field(..., ge=1, description="ID статуса из справочника spec_report_statuses")

    model_config = ConfigDict(from_attributes=True)


# ========== СХЕМЫ ДЛЯ ОТВЕТА ==========

class ReportListResponse(BaseModel):
    """Краткая информация об отчете для списков.

    Принимает либо готовый dict, либо ORM-объект Report (model_validator
    ниже расплющивает связи). Сервисный слой может возвращать ORM напрямую —
    flatten происходит здесь, в одной точке. Чтобы flatten отработал,
    relations должны быть подгружены (load_relations=True в data-слое).
    """
    id: int
    number: str
    status_id: int
    status_name: Optional[str] = None
    created_at: date
    period_id: int
    period_name: Optional[str] = None
    contract_id: int
    contract_number: Optional[str] = None
    object_id: int
    object_name: Optional[str] = None
    user_name: Optional[str] = None
    order_id: Optional[int] = None
    order_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _flatten_relations(cls, data):
        if not hasattr(data, "__table__"):
            return data
        result = {
            **{c.name: getattr(data, c.name) for c in data.__table__.columns},
            "status_name": data.status.name if data.status else None,
            "period_name": data.period.name if data.period else None,
            "contract_number": data.contract.number if data.contract else None,
            "object_name": data.object.name if data.object else None,
            "user_name": data.user.name if data.user else None,
            "order_id": data.order.id if data.order else None,
            "order_number": data.order.number if data.order else None,
            "is_signed": data.signature_status == "verified",
        }
        # Только детальный ответ: в списках object грузится без адресных
        # spec_*-цепочек (см. data/report.py::get_report_by_id).
        if "object_address" in cls.model_fields:
            # render_docx импортирует service.order — модульный импорт дал бы цикл.
            from service.render_docx import build_address
            result["object_address"] = build_address(data.object) if data.object else None
            result["object_requires_signature"] = bool(data.object and data.object.requires_signature)
            result["customer_id"] = data.contract.customer_id if data.contract else None
            result["customer_name"] = (
                data.contract.customer.name
                if data.contract and data.contract.customer else None
            )
        return result


class ReportResponse(ReportListResponse):
    """Полная информация об отчете: + user_id, description, заказчик и адрес.

    Наследует flatten-валидатор от ReportListResponse.
    """
    user_id: int
    description: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    object_address: Optional[str] = None
    # Подпись представителя заказчика узором (ПЭП)
    object_requires_signature: bool = False
    representative_id: Optional[int] = None
    signature_status: Optional[str] = None      # verified | failed
    signature_code: Optional[str] = None
    is_signed: bool = False
    signer_name: Optional[str] = None
    signer_position: Optional[str] = None
    signed_at: Optional[datetime] = None


# ========== СХЕМА ДЛЯ ВЫПАДАЮЩЕГО СПИСКА ==========

class ReportOptionResponse(BaseModel):
    """Минимальная информация об отчете для выпадающих списков"""
    id: int
    number: str
    status_id: int
    status_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)