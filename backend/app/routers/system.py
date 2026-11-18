from fastapi import APIRouter
from ..schemas.system import HealthResponse, SystemStatusResponse, OmniRouteTestRequest
from ..telemetry import get_full_system_status
from ..config import settings
from ..core.omniroute_client import OmniRouteClient

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

@router.post("/omniroute/test")
async def test_omniroute_connection(req: OmniRouteTestRequest):
    """Verifies OmniRoute API key and connectivity."""
    client = OmniRouteClient(api_key=req.api_key, base_url=req.base_url, model=req.model)
    return client.test_connection()
