"""Представители заказчика и подпись узором (ПЭП). Логика — service/customer_signature.py.

- /api/object/{id}/representatives — список, добавить (менеджер)
- /api/representative/{id} — изменить / отключить; /enroll-link — новая ссылка
- /api/public/sign-setup/{token} — без входа: представитель задаёт узор
- /api/signature/public-key, /api/signature/verify — для телефона инженера
"""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from core.dependencies import get_current_active_user
from database.database import new_session
from model.customer_representative import Customer_Representative
from model.object import Object
from model.order import Order
from model.user import User
from schema.customer_representative import (
    EnrollInfo, EnrollLinkResponse, EnrollRequest, PublicKeyResponse,
    RepresentativeCreate, RepresentativeResponse, RepresentativeUpdate,
    VerifyRequest, VerifyResponse,
)
from service import customer_signature as sig
from service.activity_log import log_activity
from service.object import check_permission

router = APIRouter(tags=["customer_signature"])


async def _rep_or_404(session, rep_id: int) -> Customer_Representative:
    rep = await session.get(Customer_Representative, rep_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Представитель не найден")
    return rep


def _link(rep, token, expires) -> EnrollLinkResponse:
    return EnrollLinkResponse(
        representative=RepresentativeResponse.model_validate(rep),
        token=token, path=f"/sign-setup/{token}", expires_at=expires,
    )


# ---------------------------------------------------------------- менеджер

@router.get("/api/object/{object_id}/representatives", response_model=List[RepresentativeResponse])
async def list_representatives(object_id: int, current_user: User = Depends(get_current_active_user)):
    await check_permission(current_user, "object_read", "просмотра представителей заказчика")
    async with new_session() as session:
        rows = (await session.execute(
            select(Customer_Representative)
            .where(Customer_Representative.object_id == object_id)
            .order_by(Customer_Representative.is_active.desc(), Customer_Representative.full_name)
        )).scalars().all()
        return [RepresentativeResponse.model_validate(r) for r in rows]


@router.post("/api/object/{object_id}/representatives", response_model=EnrollLinkResponse)
async def create_representative(object_id: int, data: RepresentativeCreate,
                                current_user: User = Depends(get_current_active_user)):
    await check_permission(current_user, "object_modify", "добавления представителей заказчика")
    async with new_session() as session:
        obj = await session.get(Object, object_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден")
        rep = Customer_Representative(object_id=object_id, **data.model_dump())
        session.add(rep)
        await session.flush()
        token, expires = sig.issue_enroll_token(rep)
        await session.commit()
        await session.refresh(rep)
        await log_activity(session, current_user, action="create", entity="object", entity_id=object_id,
                           summary=f"Добавил представителя заказчика «{rep.full_name}» на объект «{obj.name}»")
        return _link(rep, token, expires)


@router.put("/api/representative/{rep_id}", response_model=RepresentativeResponse)
async def update_representative(rep_id: int, data: RepresentativeUpdate,
                                current_user: User = Depends(get_current_active_user)):
    await check_permission(current_user, "object_modify", "изменения представителей заказчика")
    async with new_session() as session:
        rep = await _rep_or_404(session, rep_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(rep, k, v)
        await session.commit()
        await session.refresh(rep)
        return RepresentativeResponse.model_validate(rep)


@router.post("/api/representative/{rep_id}/enroll-link", response_model=EnrollLinkResponse)
async def new_enroll_link(rep_id: int, current_user: User = Depends(get_current_active_user)):
    """Новая ссылка на задание знака (старая перестаёт работать). Нужна, если
    представитель забыл знак или подпись заблокирована — снимется, когда
    знак будет задан заново."""
    await check_permission(current_user, "object_modify", "выдачи ссылки представителю")
    async with new_session() as session:
        rep = await _rep_or_404(session, rep_id)
        token, expires = sig.issue_enroll_token(rep)
        await session.commit()
        await session.refresh(rep)
        await log_activity(session, current_user, action="update", entity="object", entity_id=rep.object_id,
                           summary=f"Выдал ссылку для задания знака подписи: «{rep.full_name}»")
        return _link(rep, token, expires)


# ---------------------------------------------------------------- без входа

async def _by_token(session, token: str) -> Customer_Representative:
    rep = (await session.execute(
        select(Customer_Representative).where(Customer_Representative.enroll_token_hash == sig.token_hash(token))
    )).scalar_one_or_none()
    if not rep or not rep.is_active:
        raise HTTPException(status_code=404, detail="Ссылка недействительна — попросите новую у исполнителя")
    if rep.enroll_expires_at is None or rep.enroll_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Ссылка устарела — попросите новую у исполнителя")
    return rep


@router.get("/api/public/sign-setup/{token}", response_model=EnrollInfo)
async def enroll_info(token: str):
    async with new_session() as session:
        rep = await _by_token(session, token)
        return EnrollInfo(full_name=rep.full_name, position=rep.position,
                          object_name=rep.object.name if rep.object else "",
                          expires_at=rep.enroll_expires_at)


@router.post("/api/public/sign-setup/{token}")
async def enroll_pattern(token: str, data: EnrollRequest):
    async with new_session() as session:
        rep = await _by_token(session, token)
        sig.enroll(rep, data.pattern, data.pattern_confirm)
        await session.commit()
        return {"ok": True, "full_name": rep.full_name}


# ---------------------------------------------------------------- инженер

@router.get("/api/signature/public-key", response_model=PublicKeyResponse)
async def signature_public_key(current_user: User = Depends(get_current_active_user)):
    async with new_session() as session:
        key = await sig.get_signature_key(session)
        return PublicKeyResponse(kid=key.name, public_pem=key.public_pem)


@router.post("/api/signature/verify", response_model=VerifyResponse)
async def verify_signature(data: VerifyRequest, current_user: User = Depends(get_current_active_user)):
    """Проверить узор онлайн. Совпал — токен подписи для отчёта; нет — 400 с
    числом оставшихся попыток; заблокирован — 423."""
    await check_permission(current_user, "report_read", "подписи отчёта")
    async with new_session() as session:
        rep = await _rep_or_404(session, data.representative_id)
        order = await session.get(Order, data.order_id)
        if not order or order.object_id != rep.object_id:
            raise HTTPException(status_code=400, detail="Представитель не относится к объекту заявки")
        ok = sig._check(rep, data.pattern)
        await session.commit()
        if not ok:
            left = sig.remaining_attempts(rep)
            if rep.locked_at:
                raise HTTPException(status_code=423, detail=(
                    f"Знак не совпал. Подпись {rep.full_name} заблокирована — "
                    "менеджер может выдать новую ссылку для задания знака."))
            raise HTTPException(status_code=400, detail=f"Знак не совпал. Осталось попыток: {left}")
        signed_at = datetime.now(timezone.utc)
        return VerifyResponse(
            signature_token=sig.issue_signature_token(rep, order.id, signed_at),
            signer_name=rep.full_name, signer_position=rep.position, signed_at=signed_at,
        )
