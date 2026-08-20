"""Orchestrate the automatic test-payment workflow by order ID."""

from __future__ import annotations

import logging

from . import email_service, order_service
from .license_service import generate_license
from .models import Order, OrderStatus


logger = logging.getLogger(__name__)


def simulate_payment_success(id_order: str) -> Order:
    """Test-only payment confirmation; replace this entry point with a webhook."""
    order_service.get_order(id_order)
    return order_service.mark_order_paid(id_order)


def _create_license_from_order(id_order: str) -> Order:
    order = order_service.get_order(id_order)
    if order.paid_at is None:
        raise ValueError(f"Paid order {id_order} has no paid_at timestamp")
    result = generate_license(
        customer_name=order.name,
        email=order.email,
        mac=order.mac,
        plan=order.plan,
        paid_at=order.paid_at,
    )
    return order_service.save_license(id_order, result)


def process_payment_request(id_order: str) -> None:
    """Advance one stored order through payment, licensing, and delivery."""
    try:
        order = order_service.get_order(id_order)
        if order.status is OrderStatus.PENDING:
            email_service.send_payment_email(order)
            order = simulate_payment_success(id_order)

        if order.status is OrderStatus.PAID:
            order = _create_license_from_order(id_order)

        if order.status is OrderStatus.LICENSE_CREATED:
            try:
                email_service.send_license_email(order)
            except Exception:
                logger.exception(
                    "Could not send license email for order %s; license retained",
                    id_order,
                )
                return
            order_service.mark_license_sent(id_order)
    except Exception:
        logger.exception("Payment workflow failed for order %s", id_order)
