"""Application settings and Ed25519 private-key loading."""

from __future__ import annotations

import base64
import binascii
import os
from functools import lru_cache

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from dotenv import load_dotenv


class SettingsError(RuntimeError):
    """Raised when the server configuration is missing or invalid."""


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, binascii.Error) as exc:
        raise SettingsError("LICENSE_PRIVATE_KEY is not valid Base64URL.") from exc


@lru_cache
def get_private_key() -> Ed25519PrivateKey:
    """Load a raw 32-byte Ed25519 private key from LICENSE_PRIVATE_KEY."""
    load_dotenv()
    encoded_key = os.getenv("LICENSE_PRIVATE_KEY", "").strip()
    if not encoded_key or encoded_key == "YOUR_PRIVATE_KEY_HERE":
        raise SettingsError(
            "LICENSE_PRIVATE_KEY is missing. Copy .env.example to .env and set it."
        )

    raw_key = _base64url_decode(encoded_key)
    if len(raw_key) != 32:
        raise SettingsError("LICENSE_PRIVATE_KEY must decode to exactly 32 bytes.")

    try:
        return Ed25519PrivateKey.from_private_bytes(raw_key)
    except ValueError as exc:
        raise SettingsError("LICENSE_PRIVATE_KEY is not a valid Ed25519 key.") from exc

