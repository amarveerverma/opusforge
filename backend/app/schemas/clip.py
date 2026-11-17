from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ClipUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    crop_config: Optional[Dict[str, Any]] = None
    caption_config: Optional[Dict[str, Any]] = None

class ClipResponse(BaseModel):
    id: str
    project_id: str
    rank: int
    start_time: float
    end_time: float
    duration: float
    title: str
    hook: Optional[str] = None
    summary: Optional[str] = None
    virality_score: float
    letter_grade: str
    score_breakdown: Optional[Dict[str, Any]] = None
    transcript_excerpt: Optional[str] = None
    crop_config: Optional[Dict[str, Any]] = None
    caption_config: Optional[Dict[str, Any]] = None
    status: str
    created_at: str
    rendered: Optional[bool] = False
    render_id: Optional[str] = None
