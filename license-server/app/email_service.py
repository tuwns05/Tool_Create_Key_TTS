"""Compose and send payment and license emails over configured SMTP."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .models import Order
from .qr_service import generate_payment_qr
from .settings import SMTPSettings, get_smtp_settings


PLAN_LABELS = {"monthly": "1 tháng", "yearly": "1 năm"}


def _format_price(price: int) -> str:
    return f"{price:,}".replace(",", ".") + " VNĐ"


def _send_message(message: EmailMessage, settings: SMTPSettings) -> None:
    smtp_class = smtplib.SMTP_SSL if settings.use_ssl else smtplib.SMTP
    with smtp_class(settings.host, settings.port, timeout=settings.timeout) as smtp:
        if settings.use_tls and not settings.use_ssl:
            smtp.starttls()
        smtp.login(settings.username, settings.password)
        smtp.send_message(message)


def send_payment_email(order: Order) -> None:
    settings = get_smtp_settings()
    message = EmailMessage()
    message["Subject"] = "Yêu cầu thanh toán GPHI TTS"
    message["From"] = settings.from_address
    message["To"] = order.email
    message.set_content(
        f"""Xin chào {order.name},

Yêu cầu thanh toán GPHI TTS

Mã đơn hàng: {order.id_order}
Gói: {PLAN_LABELS[order.plan]}
Số tiền: {_format_price(order.price)}

Nội dung chuyển khoản:
{order.id_order}

Vui lòng quét QR đính kèm để thanh toán.
"""
    )
    message.add_attachment(
        generate_payment_qr(order),
        maintype="image",
        subtype="png",
        filename=f"payment-{order.id_order}.png",
    )
    _send_message(message, settings)


def send_license_email(order: Order) -> None:
    if order.license_key is None or order.expires_at is None:
        raise ValueError("Order does not have a generated license")
    settings = get_smtp_settings()
    message = EmailMessage()
    message["Subject"] = "GPHI TTS - Kích hoạt bản quyền"
    message["From"] = settings.from_address
    message["To"] = order.email
    message.set_content(
        f"""Xin chào {order.name},

Yêu cầu thanh toán của bạn đã được xử lý thành công.

Gói: {PLAN_LABELS[order.plan]}
Mã đơn hàng: {order.id_order}
Hạn sử dụng: {order.expires_at.isoformat()}

License Key:

{order.license_key}

Sao chép mã trên và nhập vào ứng dụng GPHI TTS để kích hoạt.
"""
    )
    _send_message(message, settings)
