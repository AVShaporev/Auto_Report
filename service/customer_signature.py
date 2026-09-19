"""Подпись представителя заказчика узором 4×4 — простая электронная подпись.

Как устроено:
- представитель задаёт узор сам, по одноразовой ссылке (72 ч) на своём
  телефоне — исполнитель узор не видит. Храним bcrypt(HMAC(SECRET_KEY, узор)):
  утечка БД без секрета не даёт перебрать узоры;
- онлайн: телефон инженера шлёт узор на проверку → при совпадении
  одноразовый токен подписи (JWT, 2 ч) → токен уходит с созданием/правкой
  отчёта;
- офлайн: телефон шифрует {узор, заявка, время} открытым RSA-ключом
  организации (RSA-OAEP SHA-256) и кладёт в отчёт; сервер расшифровывает и
  проверяет при синхронизации. Хеша на телефоне нет — подобрать нельзя;
- MAX_FAILED ошибок подряд → блокировка до новой ссылки;
- код подписи — HMAC(отчёт|представитель|время), 8 знаков «7F3A-91C2»:
  печатается в акте, по нему подпись находится в системе.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from config import settings
from model.app_key import App_Key
from model.customer_representative import Customer_Representative
from model.report import Report

MAX_FAILED = 5
MIN_POINTS = 5
GRID = 16                     # 4×4, точки 0..15 построчно
ENROLL_TTL = timedelta(hours=72)
TOKEN_TTL = timedelta(hours=2)
KEY_NAME = "signature"
APPROVED_STATUS_NAME = "Утверждён"

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# Узор
# ============================================================================

def normalize_pattern(points) -> str:
    if not isinstance(points, list) or not all(isinstance(p, int) for p in points):
        raise HTTPException(status_code=400, detail="Узор: нужен список точек")
    if len(points) < MIN_POINTS:
        raise HTTPException(status_code=400, detail=f"Узор слишком короткий — нужно не меньше {MIN_POINTS} точек")
    if any(p < 0 or p >= GRID for p in points) or len(set(points)) != len(points):
        raise HTTPException(status_code=400, detail="Узор: точки сетки 4×4 без повторов")
    return "-".join(str(p) for p in points)


def _prehash(pattern: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"pattern:{pattern}".encode(), hashlib.sha256).hexdigest()


def hash_pattern(points) -> str:
    return _ctx.hash(_prehash(normalize_pattern(points)))


def _check(rep: Customer_Representative, points) -> bool:
    """Проверка с учётом блокировки. Меняет счётчики — commit на вызывающем."""
    if not rep.is_active:
        raise HTTPException(status_code=400, detail="Представитель отключён")
    if not rep.pattern_hash:
        raise HTTPException(status_code=400, detail=f"{rep.full_name} ещё не задал(а) знак подписи")
    if rep.locked_at:
        raise HTTPException(status_code=423, detail=(
            f"Подпись {rep.full_name} заблокирована после {MAX_FAILED} ошибок. "
            "Менеджер может выдать новую ссылку для задания знака."))
    try:
        ok = _ctx.verify(_prehash(normalize_pattern(points)), rep.pattern_hash)
    except HTTPException:
        ok = False
    if ok:
        rep.failed_attempts = 0
        return True
    rep.failed_attempts = (rep.failed_attempts or 0) + 1
    if rep.failed_attempts >= MAX_FAILED:
        rep.locked_at = _now()
    return False


def remaining_attempts(rep: Customer_Representative) -> int:
    return max(MAX_FAILED - (rep.failed_attempts or 0), 0)


# ============================================================================
# Одноразовая ссылка на задание узора
# ============================================================================

def issue_enroll_token(rep: Customer_Representative) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    rep.enroll_token_hash = hashlib.sha256(token.encode()).hexdigest()
    rep.enroll_expires_at = _now() + ENROLL_TTL
    return token, rep.enroll_expires_at


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def enroll(rep: Customer_Representative, points, confirm) -> None:
    if rep.enroll_expires_at is None or rep.enroll_expires_at < _now():
        raise HTTPException(status_code=410, detail="Ссылка устарела — попросите новую у исполнителя")
    if normalize_pattern(points) != normalize_pattern(confirm):
        raise HTTPException(status_code=400, detail="Знаки не совпали — нарисуйте одинаково оба раза")
    rep.pattern_hash = hash_pattern(points)
    rep.pattern_set_at = _now()
    rep.failed_attempts = 0
    rep.locked_at = None
    rep.enroll_token_hash = None
    rep.enroll_expires_at = None


# ============================================================================
# Ключ организации для офлайн-подписи
# ============================================================================

async def get_signature_key(session) -> App_Key:
    key = (await session.execute(select(App_Key).where(App_Key.name == KEY_NAME))).scalar_one_or_none()
    if key:
        return key
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key = App_Key(
        name=KEY_NAME,
        private_pem=priv.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()).decode(),
        public_pem=priv.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode(),
    )
    session.add(key)
    await session.commit()
    return key


def decrypt_offline(key: App_Key, blob_b64: str) -> dict:
    """RSA-OAEP(SHA-256) → JSON {pattern: [..], order_id, signed_at, nonce}."""
    try:
        priv = serialization.load_pem_private_key(key.private_pem.encode(), password=None)
        raw = priv.decrypt(base64.b64decode(blob_b64), padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        data = json.loads(raw)
        assert isinstance(data, dict)
        return data
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Подпись: не удалось расшифровать (устаревший ключ?)")


# ============================================================================
# Токен онлайн-подписи
# ============================================================================

def issue_signature_token(rep: Customer_Representative, order_id: int, signed_at: datetime) -> str:
    return jwt.encode({
        "typ": "report_signature",
        "rep": rep.id,
        "order": order_id,
        "signed_at": signed_at.isoformat(),
        "exp": int((_now() + TOKEN_TTL).timestamp()),
    }, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def read_signature_token(token: str) -> dict:
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Подпись устарела — попросите заказчика подписать ещё раз")
    if data.get("typ") != "report_signature":
        raise HTTPException(status_code=400, detail="Неверный токен подписи")
    return data


# ============================================================================
# Подпись в отчёте
# ============================================================================

def _code(report_id: int, rep_id: int, signed_at: datetime) -> str:
    h = hmac.new(settings.SECRET_KEY.encode(), f"{report_id}|{rep_id}|{signed_at.isoformat()}".encode(),
                 hashlib.sha256).hexdigest()[:8].upper()
    return f"{h[:4]}-{h[4:]}"


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            dt = _now()
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def ensure_not_approved(report: Report) -> None:
    if report.status is not None and report.status.name == APPROVED_STATUS_NAME:
        raise HTTPException(status_code=400, detail="Отчёт утверждён — подпись изменить нельзя")


def clear_signature(report: Report) -> None:
    report.representative_id = None
    report.signature_status = None
    report.signature_code = None
    report.signer_name = None
    report.signer_position = None
    report.signed_at = None


def _set(report: Report, rep: Customer_Representative, status: str, signed_at: datetime) -> None:
    report.representative_id = rep.id
    report.signature_status = status
    report.signer_name = rep.full_name
    report.signer_position = rep.position
    report.signed_at = signed_at
    report.signature_code = _code(report.id, rep.id, signed_at) if status == "verified" else None


async def apply_signature(session, report: Report, order_id: int, *,
                          token: Optional[str] = None, offline=None) -> None:
    """Привязать подпись к отчёту (commit — на вызывающем).

    token — онлайн (узор уже проверен); offline — {representative_id,
    encrypted, signed_at} с телефона без сети: проверяем здесь. Неверный
    офлайн-узор не роняет сохранение отчёта: подпись «failed», инженер увидит.
    """
    if token:
        data = read_signature_token(token)
        if data["order"] != order_id:
            raise HTTPException(status_code=400, detail="Подпись поставлена по другой заявке")
        rep = await session.get(Customer_Representative, data["rep"])
        if not rep:
            raise HTTPException(status_code=400, detail="Представитель не найден")
        _set(report, rep, "verified", _parse_dt(data["signed_at"]))
        return
    if offline is not None:
        rep = await session.get(Customer_Representative, offline.representative_id)
        if not rep or rep.object_id != report.object_id:
            raise HTTPException(status_code=400, detail="Представитель не относится к объекту отчёта")
        key = await get_signature_key(session)
        data = decrypt_offline(key, offline.encrypted)
        if data.get("order_id") != order_id:
            raise HTTPException(status_code=400, detail="Подпись поставлена по другой заявке")
        signed_at = _parse_dt(data.get("signed_at") or offline.signed_at or _now())
        try:
            ok = _check(rep, data.get("pattern"))
        except HTTPException as e:
            if e.status_code in (400, 423):
                ok = False
            else:
                raise
        _set(report, rep, "verified" if ok else "failed", signed_at)
