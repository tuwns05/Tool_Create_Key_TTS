"""Generate the sample payment QR used by the test workflow."""

from __future__ import annotations

from io import BytesIO

import qrcode

from .models import Order


def build_payment_qr_payload(order: Order) -> str:
    return (
        f"ORDER={order.id_order}\n"
        f"AMOUNT={order.price}\n"
        f"CONTENT={order.id_order}"
    )


def generate_payment_qr(order: Order) -> bytes:
    image = qrcode.make(build_payment_qr_payload(order))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
