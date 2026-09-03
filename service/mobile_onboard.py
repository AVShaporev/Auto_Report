"""Tenant-side mint mobile-onboard-token.

Раньше эту функцию выполнял master (`Auto_Report_Master`) через
`POST /api/tenants/{slug}/mobile-onboard-token`. Теперь админ tenant'а
делает это сам из своего web-UI — master из потока выпадает
(см. saas-roadmap Backlog «Mobile QR-onboarding на стороне tenant'а»).

Секрет `MOBILE_ONBOARD_SECRET` был shared между master и tenant'ами и
уже прописан в каждом tenant.env.sops (`provision-tenant.sh`
прокидывает). Токен подписывается им, валидируется тем же секретом на
`POST /api/auth/mobile-onboard` — без изменений.
"""
from __future__ import annotations

import base64
import io
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import qrcode
from fastapi import HTTPException, status
from jose import jwt
from loguru import logger

from config import settings
from database.database import new_session
from data import user as user_data
from model.user import User

_TENANT_HOST_TEMPLATE = "{slug}.cool-doc.ru"
_MAX_TTL_MINUTES = 120
_DEFAULT_TTL_MINUTES = 30


def _tenant_slug() -> Optional[str]:
    """Slug текущего тенанта (для legacy hi-tech = 'hi-tech')."""
    return settings.TENANT_SLUG or "hi-tech"


async def mint_token(
    *,
    target_user_id: int,
    ttl_minutes: Optional[int] = None,
) -> dict:
    """Собирает HS256-JWT + QR PNG для входа юзера в mobile-приложение.

    - `target_user_id` — юзер, для которого выдаём токен.
    - `ttl_minutes` — 1..120 (default 30).

    Возвращает `dict` с ключами token/qr_url/qr_png_base64/expires_at/username/slug.
    Raises HTTPException 400/404/503.
    """
    if not settings.MOBILE_ONBOARD_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MOBILE_ONBOARD_SECRET не задан — mobile-onboarding недоступен.",
        )

    ttl = ttl_minutes or _DEFAULT_TTL_MINUTES
    if ttl <= 0 or ttl > _MAX_TTL_MINUTES:
        raise HTTPException(
            status_code=400,
            detail=f"ttl_minutes должен быть 1..{_MAX_TTL_MINUTES}",
        )

    async with new_session() as session:
        # role — lazy='joined' в User, подгружается автоматом.
        user = await user_data.get_user_by_id(session, target_user_id)
        if not user:
            raise HTTPException(
                status_code=404, detail=f"Пользователь #{target_user_id} не найден",
            )
        if not getattr(user, "is_active", True):
            raise HTTPException(
                status_code=400, detail=f"Пользователь #{target_user_id} деактивирован",
            )
        if getattr(user.role, "is_superadmin", False):
            raise HTTPException(
                status_code=400,
                detail="Superadmin не выпускается в мобильное приложение",
            )
        username = user.name

    slug = _tenant_slug()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ttl)
    payload = {
        "sub": username,
        "tenant": slug,
        "type": "mobile_onboard",
        "iat": now,
        "exp": expires_at,
        "nonce": uuid4().hex,
    }
    token = jwt.encode(payload, settings.MOBILE_ONBOARD_SECRET, algorithm="HS256")
    qr_url = f"https://{_TENANT_HOST_TEMPLATE.format(slug=slug)}/mobile-onboard?token={token}"

    # PNG QR data-URL — фронт вставляет в <img src>. box_size 8 → ~300x300 px.
    img = qrcode.make(qr_url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    qr_data_url = f"data:image/png;base64,{qr_b64}"

    logger.info(
        "mint_mobile_onboard_token: user={} slug={} ttl={}min", username, slug, ttl,
    )

    return {
        "token": token,
        "qr_url": qr_url,
        "qr_png_base64": qr_data_url,
        "expires_at": expires_at.isoformat(),
        "username": username,
        "slug": slug,
    }
