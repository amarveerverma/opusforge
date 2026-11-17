from .system import router as system_router
from .projects import router as projects_router
from .jobs import router as jobs_router
from .clips import router as clips_router
from .renders import router as renders_router
from .transcripts import router as transcripts_router

__all__ = [
    "system_router",
    "projects_router",
    "jobs_router",
    "clips_router",
    "renders_router",
    "transcripts_router",
]
