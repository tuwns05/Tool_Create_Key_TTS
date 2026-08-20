"""Create, retrieve, and transition payment orders."""

from __future__ import annotations

import secrets
import sqlite3
import string
from datetime import datetime, timezone

from .database import database_connection
from .license_service import LicenseResult
from .models import Order, OrderStatus
from .schemas import PaymentRequest


class OrderNotFoundError(LookupError):
    pass


class InvalidOrderStateError(RuntimeError):
    pass


ORDER_ALPHABET = string.ascii_uppercase + string.digits


def generate_order_id() -> str:
    return "TTS-" + "".join(secrets.choice(ORDER_ALPHABET) for _ in range(6))


def create_order(request: PaymentRequest) -> Order:
    """Insert a new PENDING order, retrying the extremely unlikely ID collision."""
    created_at = datetime.now(timezone.utc)
    for _ in range(10):
        id_order = generate_order_id()
        try:
            with database_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO orders (
                        id_order, name, email, plan, price, mac, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_order,
                        request.name,
                        str(request.email),
                        request.plan,
                        request.price,
                        request.mac,
                        OrderStatus.PENDING.value,
                        created_at.isoformat(),
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM orders WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
            if row is None:  # pragma: no cover - SQLite invariant
                raise RuntimeError("Created order could not be read back")
            return Order.from_row(row)
        except sqlite3.IntegrityError as exc:
            if "id_order" not in str(exc):
                raise
    raise RuntimeError("Could not generate a unique order ID")


def get_order(id_order: str) -> Order:
    with database_connection() as connection:
        row = connection.execute(
            "SELECT * FROM orders WHERE id_order = ?", (id_order,)
        ).fetchone()
    if row is None:
        raise OrderNotFoundError(f"Order {id_order} was not found")
    return Order.from_row(row)


def mark_order_paid(id_order: str, paid_at: datetime | None = None) -> Order:
    paid_at = paid_at or datetime.now(timezone.utc)
    if paid_at.tzinfo is None or paid_at.utcoffset() is None:
        raise ValueError("paid_at must include a timezone")
    with database_connection() as connection:
        cursor = connection.execute(
            """UPDATE orders SET status = ?, paid_at = ?
               WHERE id_order = ? AND status = ?""",
            (
                OrderStatus.PAID.value,
                paid_at.isoformat(),
                id_order,
                OrderStatus.PENDING.value,
            ),
        )
    if cursor.rowcount != 1:
        current = get_order(id_order)
        if current.status is not OrderStatus.PAID:
            raise InvalidOrderStateError(
                f"Order {id_order} cannot move from {current.status} to PAID"
            )
    return get_order(id_order)


def save_license(id_order: str, result: LicenseResult) -> Order:
    with database_connection() as connection:
        cursor = connection.execute(
            """UPDATE orders
               SET status = ?, license_key = ?, expires_at = ?
               WHERE id_order = ? AND status = ?""",
            (
                OrderStatus.LICENSE_CREATED.value,
                result.license_key,
                result.expires_at.isoformat(),
                id_order,
                OrderStatus.PAID.value,
            ),
        )
    if cursor.rowcount != 1:
        current = get_order(id_order)
        raise InvalidOrderStateError(
            f"Order {id_order} cannot move from {current.status} to LICENSE_CREATED"
        )
    return get_order(id_order)


def mark_license_sent(id_order: str) -> Order:
    with database_connection() as connection:
        cursor = connection.execute(
            """UPDATE orders SET status = ?
               WHERE id_order = ? AND status = ?""",
            (
                OrderStatus.LICENSE_SENT.value,
                id_order,
                OrderStatus.LICENSE_CREATED.value,
            ),
        )
    if cursor.rowcount != 1:
        current = get_order(id_order)
        raise InvalidOrderStateError(
            f"Order {id_order} cannot move from {current.status} to LICENSE_SENT"
        )
    return get_order(id_order)
