"""
ClipForge SQLite Database Manager with WAL mode and schema migration
"""
import sqlite3
import aiosqlite
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from .config import settings

logger = logging.getLogger("clipforge.database")

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    source_file_path TEXT NOT NULL,
    duration REAL DEFAULT 0.0,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    fps REAL DEFAULT 0.0,
    codec TEXT,
    instructions TEXT,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage TEXT NOT NULL DEFAULT 'pending',
    progress REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL DEFAULT 1,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    title TEXT NOT NULL,
    hook TEXT,
    summary TEXT,
    virality_score REAL NOT NULL DEFAULT 0.0,
    letter_grade TEXT NOT NULL DEFAULT 'B',
    score_breakdown_json TEXT,
    transcript_excerpt TEXT,
    crop_config_json TEXT,
    caption_config_json TEXT,
    status TEXT NOT NULL DEFAULT 'suggested',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS renders (
    id TEXT PRIMARY KEY,
    clip_id TEXT NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    output_file_path TEXT NOT NULL,
    width INTEGER NOT NULL DEFAULT 1080,
    height INTEGER NOT NULL DEFAULT 1920,
    fps REAL NOT NULL DEFAULT 30.0,
    duration REAL NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    encoder_used TEXT NOT NULL DEFAULT 'h264_nvenc',
    quality_report_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_clips_project ON clips(project_id);
CREATE INDEX IF NOT EXISTS idx_renders_clip ON renders(clip_id);
"""

def init_db_sync():
    """Synchronously initializes database and verifies WAL mode."""
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(settings.DB_PATH)) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    logger.info("Database initialized with WAL mode at %s", settings.DB_PATH)

# Initialize schema immediately upon module import
init_db_sync()

@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Asynchronous context manager yielding an aiosqlite connection with Row factory."""
    async with aiosqlite.connect(str(settings.DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db
