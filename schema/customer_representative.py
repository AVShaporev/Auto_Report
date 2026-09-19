"""Схемы: представители заказчика и подпись узором (ПЭП)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RepresentativeCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    position: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=150)


class RepresentativeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    position: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=150)
    is_active: Optional[bool] = None


class RepresentativeResponse(BaseModel):
    id: int
    object_id: int
    full_name: str
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    has_pattern: bool
    is_locked: bool
    pattern_set_at: Optional[datetime] = None
    enroll_expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EnrollLinkResponse(BaseModel):
    """Ссылку целиком собирает фронт: <origin>/sign-setup/<token>."""
    representative: RepresentativeResponse
    token: str
    path: str
    expires_at: datetime


class EnrollInfo(BaseModel):
    full_name: str
    position: Optional[str] = None
    object_name: str
    expires_at: datetime


class EnrollRequest(BaseModel):
    pattern: List[int] = Field(..., min_length=1, max_length=16)
    pattern_confirm: List[int] = Field(..., min_length=1, max_length=16)


class VerifyRequest(BaseModel):
    representative_id: int = Field(..., ge=1)
    order_id: int = Field(..., ge=1)
    pattern: List[int] = Field(..., min_length=1, max_length=16)


class VerifyResponse(BaseModel):
    signature_token: str
    signer_name: str
    signer_position: Optional[str] = None
    signed_at: datetime


class PublicKeyResponse(BaseModel):
    kid: str
    public_pem: str
