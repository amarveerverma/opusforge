from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    instructions: Optional[str] = Field(None, max_length=2000)

class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    instructions: Optional[str] = Field(None, max_length=2000)

class ProjectResponse(BaseModel):
    id: str
    title: str
    original_filename: str
    source_file_path: str
    duration: float
    width: int
    height: int
    fps: float
    codec: Optional[str] = None
    instructions: Optional[str] = None
    status: str
    created_at: str
    updated_at: str
    clips_count: Optional[int] = 0

class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
