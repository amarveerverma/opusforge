"""
ClipForge FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import init_db_sync
from .routers import (
    system_router,
    projects_router,
    jobs_router,
    clips_router,
    renders_router,
    transcripts_router,
    analysis_router,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("clipforge")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting ClipForge backend...")
    init_db_sync()
    logger.info("ClipForge backend startup complete. Serving on http://%s:%s", settings.HOST, settings.PORT)
    yield
    logger.info("Shutting down ClipForge backend...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local AI Video Repurposing Studio API",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open local development access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred", "error": str(exc)},
    )

# Register API routers
app.include_router(system_router)
app.include_router(projects_router)
app.include_router(jobs_router)
app.include_router(clips_router)
app.include_router(renders_router)
app.include_router(transcripts_router)
app.include_router(analysis_router)

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "ready",
        "docs_url": "/docs",
    }
