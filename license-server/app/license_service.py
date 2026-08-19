"""License payload creation and Ed25519 signing."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from dateutil.relativedelta import relativedelta

from .settings import get_private_key


Plan = Literal["monthly", "yearly"]


@dataclass(frozen=True)
class LicenseResult:
    license_key: str
    expires_at: datetime
    payload: dict[str, object]


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_license(
    customer_name: str,
    email: str,
    mac: str,
    plan: Plan,
    paid_at: datetime,
) -> LicenseResult:
    """Build a canonical payload and sign its exact UTF-8 bytes."""
    if paid_at.tzinfo is None or paid_at.utcoffset() is None:
        raise ValueError("paid_at must include a timezone")
    if plan not in ("monthly", "yearly"):
        raise ValueError("plan must be monthly or yearly")

    expires_at = paid_at + relativedelta(months=1 if plan == "monthly" else 0, years=1 if plan == "yearly" else 0)
    payload: dict[str, object] = {
        "v": 1,
        "customer_name": customer_name,
        "email": email,
        "mac": mac.upper(),
        "plan": plan,
        "paid_at": paid_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    payload_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    signature = get_private_key().sign(payload_bytes)
    license_key = f"{base64url_encode(payload_bytes)}.{base64url_encode(signature)}"
    return LicenseResult(license_key, expires_at, payload)

