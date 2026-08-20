"""FastAPI entry point for the local license server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException

from .database import initialize_database
from .license_service import generate_license
from .order_service import create_order
from .payment_service import process_payment_request
from .schemas import (
    HealthResponse,
    LicenseRequest,
    LicenseResponse,
    PaymentRequest,
    PaymentResponse,
)
from .settings import SettingsError


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(
    title="TTS License Server",
    description="Test payment flow and Ed25519 license generator for GPHI TTS.",
    version="1.1.0",
    lifespan=lifespan,
)


PAYMENT_ACCEPTED_MESSAGE = (
    "Yêu cầu thanh toán đã được tiếp nhận. Vui lòng kiểm tra email."
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/license/generate", response_model=LicenseResponse, tags=["License"])
def create_license(request: LicenseRequest) -> LicenseResponse:
    try:
        result = generate_license(
            customer_name=request.customer_name,
            email=str(request.email),
            mac=request.mac,
            plan=request.plan,
            paid_at=request.paid_at,
        )
    except SettingsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return LicenseResponse(license_key=result.license_key, payload=result.payload)


@app.post("/payment/request", response_model=PaymentResponse, tags=["Payment"])
def request_payment(
    request: PaymentRequest, background_tasks: BackgroundTasks
) -> PaymentResponse:
    order = create_order(request)
    background_tasks.add_task(process_payment_request, order.id_order)
    return PaymentResponse(
        id_order=order.id_order,
        message=PAYMENT_ACCEPTED_MESSAGE,
    )

