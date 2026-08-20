"""Application settings, SMTP configuration, and private-key loading."""

from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from dotenv import load_dotenv


class SettingsError(RuntimeError):
    """Raised when the server configuration is missing or invalid."""


@dataclass(frozen=True)
class SMTPSettings:
    host: str
    port: int
    username: str
    password: str
    from_address: str
    use_tls: bool
    use_ssl: bool
    timeout: float


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SettingsError(f"{name} must be true or false.")


def get_database_path() -> Path:
    """Return the configured SQLite file path."""
    load_dotenv()
    value = os.getenv("SQLITE_PATH", "orders.db").strip()
    if not value:
        raise SettingsError("SQLITE_PATH must not be blank.")
    return Path(value).expanduser()


def get_smtp_settings() -> SMTPSettings:
    """Load SMTP settings only when an email actually needs to be sent."""
    load_dotenv()
    required = {
        "SMTP_HOST": os.getenv("SMTP_HOST", "").strip(),
        "SMTP_USERNAME": os.getenv("SMTP_USERNAME", "").strip(),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", "").strip(),
        "SMTP_FROM": os.getenv("SMTP_FROM", "").strip(),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SettingsError(f"Missing SMTP configuration: {', '.join(missing)}")

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        timeout = float(os.getenv("SMTP_TIMEOUT", "30"))
    except ValueError as exc:
        raise SettingsError("SMTP_PORT and SMTP_TIMEOUT must be numeric.") from exc
    if not 1 <= port <= 65535 or timeout <= 0:
        raise SettingsError("SMTP_PORT or SMTP_TIMEOUT is outside its valid range.")

    use_tls = _env_bool("SMTP_USE_TLS", True)
    use_ssl = _env_bool("SMTP_USE_SSL", False)
    if use_tls and use_ssl:
        raise SettingsError("SMTP_USE_TLS and SMTP_USE_SSL cannot both be true.")

    return SMTPSettings(
        host=required["SMTP_HOST"],
        port=port,
        username=required["SMTP_USERNAME"],
        password=required["SMTP_PASSWORD"],
        from_address=required["SMTP_FROM"],
        use_tls=use_tls,
        use_ssl=use_ssl,
        timeout=timeout,
    )


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

