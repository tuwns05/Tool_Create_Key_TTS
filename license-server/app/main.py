"""FastAPI entry point for the local license server."""

from fastapi import FastAPI, HTTPException

from .license_service import generate_license
from .schemas import HealthResponse, LicenseRequest, LicenseResponse
from .settings import SettingsError


app = FastAPI(
    title="TTS License Server",
    description="Local-only Ed25519 license generator for TTS testing.",
    version="1.0.0",
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

