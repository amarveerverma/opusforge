from fastapi import APIRouter
from ..schemas.system import HealthResponse, SystemStatusResponse
from ..telemetry import get_full_system_status
from ..config import settings

router = APIRouter(tags=["System"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Lightweight health check endpoint."""
    return HealthResponse(
        status="healthy",
        app=settings.APP_NAME,
        version=settings.APP_VERSION
    )

@router.get("/system/status", response_model=SystemStatusResponse)
async def system_status():
    """Returns live hardware telemetry (GPU VRAM, Utilization, RAM, Disk)."""
    return get_full_system_status()
