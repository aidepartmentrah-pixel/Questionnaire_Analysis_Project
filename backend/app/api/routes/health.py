from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Stable liveness/readiness payload used by the frontend's health indicator."""
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
        version=APP_VERSION,
    )
