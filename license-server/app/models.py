"""Database model used by the payment workflow."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal


Plan = Literal["monthly", "yearly"]


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    LICENSE_CREATED = "LICENSE_CREATED"
    LICENSE_SENT = "LICENSE_SENT"


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


@dataclass(frozen=True)
class Order:
    id: int
    id_order: str
    name: str
    email: str
    plan: Plan
    price: int
    mac: str
    status: OrderStatus
    created_at: datetime
    paid_at: datetime | None
    expires_at: datetime | None
    license_key: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Order":
        return cls(
            id=row["id"],
            id_order=row["id_order"],
            name=row["name"],
            email=row["email"],
            plan=row["plan"],
            price=row["price"],
            mac=row["mac"],
            status=OrderStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            paid_at=_parse_datetime(row["paid_at"]),
            expires_at=_parse_datetime(row["expires_at"]),
            license_key=row["license_key"],
        )
