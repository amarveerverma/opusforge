from pydantic import BaseModel
from typing import Optional

class JobResponse(BaseModel):
    id: str
    project_id: str
    stage: str
    progress: float
    status: str
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
