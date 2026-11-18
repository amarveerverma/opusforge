from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class GpuStatus(BaseModel):
    name: str
    available: bool
    vram_total_mb: int
    vram_used_mb: int
    vram_free_mb: int
    utilization_percent: int
    temperature_c: int

class RamStatus(BaseModel):
    total_gb: float
    available_gb: float
    used_gb: float
    percent: float

class DiskStatus(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    percent_free: float

class SystemStatusResponse(BaseModel):
    status: str
    gpu: GpuStatus
    ram: RamStatus
    disk: DiskStatus
    encoders: List[str]

class HealthResponse(BaseModel):
    status: str
    app: str
    version: str

class OmniRouteTestRequest(BaseModel):
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
