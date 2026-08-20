from __future__ import annotations

import base64
import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import email_service, payment_service
from app.database import database_connection
from app.main import app
from app.models import OrderStatus
from app.order_service import create_order, get_order
from app.qr_service import build_payment_qr_payload, generate_payment_qr
from app.schemas import PaymentRequest
from app.settings import SMTPSettings


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "orders.db"))


def payment_request(**overrides: object) -> PaymentRequest:
    payload: dict[str, object] = {
        "name": "Nguyen Van A",
        "email": "abc@gmail.com",
        "plan": "yearly",
        "price": 1_990_000,
        "mac": "F0:68:E3:C4:D1:A1",
    }
    payload.update(overrides)
    return PaymentRequest.model_validate(payload)


def payment_json(**overrides: object) -> dict[str, object]:
    return payment_request(**overrides).model_dump(mode="json")


def order_count() -> int:
    with database_connection() as connection:
        return connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]


def decode_license_payload(license_key: str) -> dict[str, object]:
    payload_part = license_key.split(".", maxsplit=1)[0]
    raw = base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4))
    return json.loads(raw)


def test_create_order_is_unique_and_initially_pending() -> None:
    first = create_order(payment_request())
    second = create_order(payment_request())

    assert first.id_order.startswith("TTS-")
    assert first.id_order != second.id_order
    assert first.status is OrderStatus.PENDING
    assert first.paid_at is None
    assert first.expires_at is None
    assert first.license_key is None


def test_payment_email_uses_order_recipient(monkeypatch: pytest.MonkeyPatch) -> None:
    order = create_order(payment_request(email="buyer@example.com"))
    sent_messages = []
    settings = SMTPSettings(
        host="smtp.example.com",
        port=587,
        username="user",
        password="secret",
        from_address="sales@example.com",
        use_tls=True,
        use_ssl=False,
        timeout=30,
    )
    monkeypatch.setattr(email_service, "get_smtp_settings", lambda: settings)
    monkeypatch.setattr(
        email_service,
        "_send_message",
        lambda message, smtp_settings: sent_messages.append(message),
    )

    email_service.send_payment_email(order)

    assert sent_messages[0]["To"] == order.email == "buyer@example.com"
    assert order.id_order in sent_messages[0].get_body().get_content()


def test_qr_contains_order_id_and_price() -> None:
    order = create_order(payment_request())
    payload = build_payment_qr_payload(order)

    assert payload == (
        f"ORDER={order.id_order}\nAMOUNT=1990000\nCONTENT={order.id_order}"
    )
    assert generate_payment_qr(order).startswith(b"\x89PNG\r\n\x1a\n")


def test_simulated_payment_reads_order_and_marks_it_paid() -> None:
    order = create_order(payment_request())

    paid = payment_service.simulate_payment_success(order.id_order)

    assert paid.status is OrderStatus.PAID
    assert paid.paid_at is not None
    assert paid.paid_at.utcoffset() is not None


def test_full_api_workflow_creates_and_emails_license(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment_recipients: list[str] = []
    license_recipients: list[str] = []
    monkeypatch.setattr(
        email_service,
        "send_payment_email",
        lambda order: payment_recipients.append(order.email),
    )
    monkeypatch.setattr(
        email_service,
        "send_license_email",
        lambda order: license_recipients.append(order.email),
    )

    response = client.post("/payment/request", json=payment_json())

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "success": True,
        "id_order": body["id_order"],
        "message": "Yêu cầu thanh toán đã được tiếp nhận. Vui lòng kiểm tra email.",
    }
    assert "license_key" not in body

    order = get_order(body["id_order"])
    assert order.status is OrderStatus.LICENSE_SENT
    assert order.paid_at is not None
    assert order.expires_at is not None
    assert order.license_key is not None
    assert payment_recipients == [order.email]
    assert license_recipients == [order.email]

    payload = decode_license_payload(order.license_key)
    assert payload["customer_name"] == order.name
    assert payload["email"] == order.email
    assert payload["mac"] == order.mac
    assert payload["plan"] == order.plan
    assert datetime.fromisoformat(payload["paid_at"]) == order.paid_at


def test_license_email_failure_retains_key_and_order_for_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment_calls: list[str] = []
    monkeypatch.setattr(
        email_service,
        "send_payment_email",
        lambda order: payment_calls.append(order.id_order),
    )

    def fail_license_email(order) -> None:
        raise OSError("SMTP unavailable")

    monkeypatch.setattr(email_service, "send_license_email", fail_license_email)

    response = client.post("/payment/request", json=payment_json())
    id_order = response.json()["id_order"]
    order = get_order(id_order)

    assert response.status_code == 200
    assert order.status is OrderStatus.LICENSE_CREATED
    assert order.license_key is not None
    original_key = order.license_key
    assert order_count() == 1

    payment_service.process_payment_request(id_order)

    retried = get_order(id_order)
    assert retried.license_key == original_key
    assert retried.status is OrderStatus.LICENSE_CREATED
    assert order_count() == 1
    assert payment_calls == [id_order]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("email", "invalid"),
        ("plan", "weekly"),
        ("price", 0),
        ("mac", "F0-68-E3-C4-D1-A1"),
    ],
)
def test_payment_request_validation(field: str, value: object) -> None:
    payload = payment_json()
    payload[field] = value
    response = client.post("/payment/request", json=payload)
    assert response.status_code == 422
    assert order_count() == 0
