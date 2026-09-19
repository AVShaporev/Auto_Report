"""Подпись представителя заказчика узором 4×4 (ПЭП), 1.0.70."""
import base64
import json
import re
from datetime import date

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from httpx import AsyncClient

from model.object import Object
from model.order import Order
from model.spec_order import Spec_Order
from model.spec_order_status import Spec_Order_Status
from model.spec_report_status import Spec_Report_Status
from service import render_docx

PATTERN = [0, 1, 5, 10, 15]
WRONG = [3, 2, 1, 0, 4]


async def _seed(db_session, ref, user, *, requires_signature=False):
    plan = Spec_Order(name="Плановое ТО", short_name="ТО", code="plan", sla_kind="manual")
    st = Spec_Order_Status(name="Новая", is_default=True)
    work = Spec_Report_Status(name="В работе", is_default=True)
    submitted = Spec_Report_Status(name="На утверждении")
    approved = Spec_Report_Status(name="Утверждён")
    db_session.add_all([plan, st, work, submitted, approved])
    await db_session.commit()
    order = Order(number="1/09/2026/ТО/1", spec_order_id=plan.id, contract_id=ref["contract"].id,
                  object_id=ref["object"].id, user_id=user.id, status_id=st.id, created_at=date(2026, 9, 1))
    db_session.add(order)
    obj = await db_session.get(Object, ref["object"].id)
    obj.requires_signature = requires_signature
    await db_session.commit()
    return {"order_id": order.id, "object_id": ref["object"].id,
            "submitted_id": submitted.id, "approved_id": approved.id}


async def _rep_with_pattern(client, h, object_id):
    resp = await client.post(f"/api/object/{object_id}/representatives", headers=h,
                             json={"full_name": "Орлова Мария Сергеевна", "position": "Главный инженер"})
    assert resp.status_code == 200, resp.text
    link = resp.json()
    resp = await client.post(f"/api/public/sign-setup/{link['token']}",
                             json={"pattern": PATTERN, "pattern_confirm": PATTERN})
    assert resp.status_code == 200, resp.text
    return link["representative"]["id"]


async def test_enroll_by_link(client: AsyncClient, db_session, superadmin_token, superadmin_user,
                              auth_headers, reference_data):
    h = auth_headers(superadmin_token)
    seeded = await _seed(db_session, reference_data, superadmin_user["user"])
    resp = await client.post(f"/api/object/{seeded['object_id']}/representatives", headers=h,
                             json={"full_name": "Орлова Мария Сергеевна", "position": "Главный инженер"})
    link = resp.json()
    assert link["path"] == f"/sign-setup/{link['token']}"
    assert link["representative"]["has_pattern"] is False

    resp = await client.get(f"/api/public/sign-setup/{link['token']}")
    assert resp.status_code == 200 and resp.json()["full_name"] == "Орлова Мария Сергеевна"

    resp = await client.post(f"/api/public/sign-setup/{link['token']}",
                             json={"pattern": PATTERN, "pattern_confirm": WRONG})
    assert resp.status_code == 400 and "не совпали" in resp.json()["detail"]
    resp = await client.post(f"/api/public/sign-setup/{link['token']}",
                             json={"pattern": [0, 1, 2], "pattern_confirm": [0, 1, 2]})
    assert resp.status_code == 400 and "короткий" in resp.json()["detail"]
    resp = await client.post(f"/api/public/sign-setup/{link['token']}",
                             json={"pattern": PATTERN, "pattern_confirm": PATTERN})
    assert resp.status_code == 200
    # Ссылка одноразовая
    resp = await client.get(f"/api/public/sign-setup/{link['token']}")
    assert resp.status_code == 404

    resp = await client.get(f"/api/object/{seeded['object_id']}/representatives", headers=h)
    rep = resp.json()[0]
    assert rep["has_pattern"] is True and rep["is_locked"] is False
    assert "pattern_hash" not in rep


async def test_online_signature_to_report_and_act(client: AsyncClient, db_session, superadmin_token,
                                                  superadmin_user, auth_headers, reference_data):
    h = auth_headers(superadmin_token)
    seeded = await _seed(db_session, reference_data, superadmin_user["user"])
    rep_id = await _rep_with_pattern(client, h, seeded["object_id"])

    resp = await client.post("/api/signature/verify", headers=h,
                             json={"representative_id": rep_id, "order_id": seeded["order_id"], "pattern": WRONG})
    assert resp.status_code == 400 and "Осталось попыток: 4" in resp.json()["detail"]
    resp = await client.post("/api/signature/verify", headers=h,
                             json={"representative_id": rep_id, "order_id": seeded["order_id"], "pattern": PATTERN})
    assert resp.status_code == 200, resp.text
    token = resp.json()["signature_token"]

    resp = await client.post("/api/report/create", headers=h, json={
        "order_id": seeded["order_id"], "report_period": "2026-09", "signature_token": token})
    assert resp.status_code == 200, resp.text
    rep = resp.json()
    assert rep["signature_status"] == "verified" and rep["is_signed"] is True
    assert rep["signer_name"] == "Орлова Мария Сергеевна"
    assert re.fullmatch(r"[0-9A-F]{4}-[0-9A-F]{4}", rep["signature_code"])

    order = await render_docx._load_order_for_docx(db_session, seeded["order_id"])
    ctx = render_docx._build_context(order)
    assert ctx["report"]["signature_line"].startswith(
        "Подписано простой электронной подписью: Орлова Мария Сергеевна, Главный инженер,")
    assert rep["signature_code"] in ctx["report"]["signature_line"]

    # Убрать подпись
    resp = await client.put(f"/api/report/{rep['id']}", headers=h, json={"clear_signature": True})
    assert resp.status_code == 200 and resp.json()["signature_status"] is None


async def test_lockout_and_unlock_by_new_link(client: AsyncClient, db_session, superadmin_token,
                                              superadmin_user, auth_headers, reference_data):
    h = auth_headers(superadmin_token)
    seeded = await _seed(db_session, reference_data, superadmin_user["user"])
    rep_id = await _rep_with_pattern(client, h, seeded["object_id"])
    body = {"representative_id": rep_id, "order_id": seeded["order_id"], "pattern": WRONG}
    codes = [(await client.post("/api/signature/verify", headers=h, json=body)).status_code for _ in range(5)]
    assert codes == [400, 400, 400, 400, 423]
    body["pattern"] = PATTERN
    resp = await client.post("/api/signature/verify", headers=h, json=body)
    assert resp.status_code == 423  # верный знак не помогает — заблокировано

    resp = await client.post(f"/api/representative/{rep_id}/enroll-link", headers=h)
    token = resp.json()["token"]
    await client.post(f"/api/public/sign-setup/{token}", json={"pattern": PATTERN, "pattern_confirm": PATTERN})
    resp = await client.post("/api/signature/verify", headers=h, json=body)
    assert resp.status_code == 200


def _encrypt(public_pem: str, payload: dict) -> str:
    pub = serialization.load_pem_public_key(public_pem.encode())
    return base64.b64encode(pub.encrypt(json.dumps(payload).encode(), padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))).decode()


async def test_offline_signature_checked_on_sync(client: AsyncClient, db_session, superadmin_token,
                                                 superadmin_user, auth_headers, reference_data):
    h = auth_headers(superadmin_token)
    seeded = await _seed(db_session, reference_data, superadmin_user["user"])
    rep_id = await _rep_with_pattern(client, h, seeded["object_id"])
    pem = (await client.get("/api/signature/public-key", headers=h)).json()["public_pem"]

    wrong = _encrypt(pem, {"pattern": WRONG, "order_id": seeded["order_id"],
                           "signed_at": "2026-09-18T11:32:00+03:00", "nonce": "a1"})
    resp = await client.post("/api/report/create", headers=h, json={
        "order_id": seeded["order_id"], "report_period": "2026-09",
        "signature_offline": {"representative_id": rep_id, "encrypted": wrong}})
    assert resp.status_code == 200, resp.text   # отчёт сохранён, подпись — нет
    rep = resp.json()
    assert rep["signature_status"] == "failed" and rep["signature_code"] is None

    good = _encrypt(pem, {"pattern": PATTERN, "order_id": seeded["order_id"],
                          "signed_at": "2026-09-18T11:40:00+03:00", "nonce": "b2"})
    resp = await client.put(f"/api/report/{rep['id']}", headers=h, json={
        "signature_offline": {"representative_id": rep_id, "encrypted": good}})
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_status"] == "verified"
    assert resp.json()["signed_at"].startswith("2026-09-18T08:40")  # время с телефона, UTC


async def test_object_flag_blocks_submit_without_signature(client: AsyncClient, db_session, superadmin_token,
                                                           superadmin_user, auth_headers, reference_data):
    h = auth_headers(superadmin_token)
    seeded = await _seed(db_session, reference_data, superadmin_user["user"], requires_signature=True)
    rep_id = await _rep_with_pattern(client, h, seeded["object_id"])
    resp = await client.post("/api/report/create", headers=h, json={
        "order_id": seeded["order_id"], "report_period": "2026-09"})
    rid = resp.json()["id"]

    for status_id in (seeded["submitted_id"], seeded["approved_id"]):
        resp = await client.patch(f"/api/report/{rid}/status", headers=h, json={"status_id": status_id})
        assert resp.status_code == 400 and "подпись представителя" in resp.json()["detail"]

    token = (await client.post("/api/signature/verify", headers=h, json={
        "representative_id": rep_id, "order_id": seeded["order_id"], "pattern": PATTERN})).json()["signature_token"]
    await client.put(f"/api/report/{rid}", headers=h, json={"signature_token": token})
    resp = await client.patch(f"/api/report/{rid}/status", headers=h, json={"status_id": seeded["submitted_id"]})
    assert resp.status_code == 200, resp.text
