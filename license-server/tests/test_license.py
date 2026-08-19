from __future__ import annotations

import base64
import os

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi.testclient import TestClient

os.environ["LICENSE_PRIVATE_KEY"] = "4BI0ollUUzAioL_OdBEiq6at8zDb58ZbEhD4UtkgMgk"

from app.main import app  # noqa: E402
from app.settings import get_private_key  # noqa: E402


TEST_PUBLIC_KEY = "KpKH0Ng-3UJLEbEktxTBcWn4p_V1smDJ5K5kkhbbf4A"
client = TestClient(app)


def decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@pytest.fixture(autouse=True)
def use_test_private_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "LICENSE_PRIVATE_KEY", "4BI0ollUUzAioL_OdBEiq6at8zDb58ZbEhD4UtkgMgk"
    )
    get_private_key.cache_clear()
    yield
    get_private_key.cache_clear()


def request_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "customer_name": "Test Customer",
        "email": "test@example.com",
        "mac": "F0:68:E3:C4:D1:A1",
        "plan": "yearly",
        "paid_at": "2026-08-19T23:50:00+07:00",
    }
    payload.update(overrides)
    return payload


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_yearly_expiration() -> None:
    response = client.post("/license/generate", json=request_payload())
    assert response.status_code == 200
    assert response.json()["payload"]["expires_at"] == "2027-08-19T23:50:00+07:00"


def test_monthly_expiration() -> None:
    response = client.post(
        "/license/generate", json=request_payload(plan="monthly")
    )
    assert response.status_code == 200
    assert response.json()["payload"]["expires_at"] == "2026-09-19T23:50:00+07:00"


def test_lowercase_mac_is_normalized() -> None:
    response = client.post(
        "/license/generate", json=request_payload(mac="f0:68:e3:c4:d1:a1")
    )
    assert response.status_code == 200
    assert response.json()["payload"]["mac"] == "F0:68:E3:C4:D1:A1"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("customer_name", "   "),
        ("email", "not-an-email"),
        ("mac", "F0-68-E3-C4-D1-A1"),
        ("plan", "weekly"),
        ("paid_at", "2026-08-19T23:50:00"),
    ],
)
def test_invalid_input_is_rejected(field: str, value: str) -> None:
    response = client.post("/license/generate", json=request_payload(**{field: value}))
    assert response.status_code == 422


def test_signature_verifies_and_tampering_fails() -> None:
    response = client.post("/license/generate", json=request_payload())
    assert response.status_code == 200
    payload_part, signature_part = response.json()["license_key"].split(".")
    payload_bytes = decode_base64url(payload_part)
    signature = decode_base64url(signature_part)
    public_key = Ed25519PublicKey.from_public_bytes(decode_base64url(TEST_PUBLIC_KEY))

    public_key.verify(signature, payload_bytes)

    tampered = bytearray(payload_bytes)
    tampered[0] ^= 1
    with pytest.raises(InvalidSignature):
        public_key.verify(signature, bytes(tampered))


def test_missing_private_key_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LICENSE_PRIVATE_KEY")
    get_private_key.cache_clear()
    response = client.post("/license/generate", json=request_payload())
    assert response.status_code == 500
    assert "LICENSE_PRIVATE_KEY is missing" in response.json()["detail"]

