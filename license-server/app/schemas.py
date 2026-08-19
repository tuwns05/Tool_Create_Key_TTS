"""Pydantic request and response contracts."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


MAC_PATTERN = re.compile(r"^[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}$")


class LicenseRequest(BaseModel):
    customer_name: str = Field(min_length=1, examples=["Test Customer"])
    email: EmailStr = Field(examples=["test@example.com"])
    mac: str = Field(examples=["F0:68:E3:C4:D1:A1"])
    plan: Literal["monthly", "yearly"]
    paid_at: datetime = Field(examples=["2026-08-19T23:50:00+07:00"])

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("customer_name must not be blank")
        return value

    @field_validator("mac")
    @classmethod
    def validate_mac(cls, value: str) -> str:
        value = value.strip()
        if not MAC_PATTERN.fullmatch(value):
            raise ValueError("mac must use the format XX:XX:XX:XX:XX:XX")
        return value.upper()

    @field_validator("paid_at")
    @classmethod
    def validate_paid_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("paid_at must include an ISO 8601 timezone offset")
        return value


class LicensePayload(BaseModel):
    v: int = 1
    customer_name: str
    email: EmailStr
    mac: str
    plan: Literal["monthly", "yearly"]
    paid_at: datetime
    expires_at: datetime


class LicenseResponse(BaseModel):
    license_key: str
    payload: LicensePayload


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"

