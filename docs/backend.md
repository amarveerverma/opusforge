# ClipForge — Backend Architecture & Implementation Guide

## 1. Stack & Runtime
- **Framework**: FastAPI (Python 3.11) with Uvicorn ASGI server.
- **Package & Environment Management**: Astral `uv` for lightning-fast virtual environment creation and deterministic dependency locking.
- **Data Validation & Serializers**: Pydantic V2 schemas for every request and response model.
- **Asynchronous Task Worker**: Background task executor with concurrency throttling (max 1 concurrent GPU-intensive job).

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization, CORS, routers
│   ├── config.py            # Settings, paths, environment variables
│   ├── database.py          # SQLite connection, session factory, migrations
│   ├── models/              # SQLAlchemy / SQL models
│   │   ├── project.py
│   │   ├── job.py
│   │   ├── clip.py
│   │   └── render.py
│   ├── schemas/             # Pydantic validation schemas
│   │   ├── project.py
│   │   ├── job.py
│   │   ├── clip.py
│   │   └── system.py
│   ├── api/                 # API route handlers
│   │   ├── system.py
│   │   ├── projects.py
│   │   ├── jobs.py
│   │   ├── clips.py
│   │   └── renders.py
│   ├── core/                # Business logic & pipeline stages
│   │   ├── ingestion.py     # FFprobe, validation, thumbnails
│   │   ├── transcriber.py   # WhisperX / faster-whisper on CUDA
│   │   ├── diarization.py   # pyannote.audio speaker extraction
│   │   ├── scene_detect.py  # PySceneDetect cut detection
│   │   ├── face_tracker.py  # MediaPipe face bounding boxes
│   │   ├── arc_discovery.py # Narrative boundary & hook search
│   │   ├── virality_score.py# Scoring engine (Hook/Flow/Value)
│   │   ├── reframer.py      # 9:16 crop calculation & smoothing
│   │   ├── subtitles.py     # ASS word-synced karaoke generator
│   │   └── renderer.py      # FFmpeg NVENC execution & quality audit
│   └── utils/
│       ├── hardware.py      # GPU VRAM, RAM, CPU telemetry
│       ├── memory.py        # VRAM eviction & GC helpers
│       └── file_system.py   # Path validation, safe filenames
├── requirements.txt
└── pyproject.toml
```

---

## 3. Reliability & Guardrails
- **Path Traversal Protection**: All file paths are strictly resolved against `c:\clipper\data\`. Any attempt to access outside paths results in `403 Forbidden`.
- **Safe Subprocess Invocations**: FFmpeg and other CLI utilities are invoked using sanitized argument lists (e.g. `subprocess.run([...])`), never raw shell strings (`shell=True` is prohibited).
- **Graceful Error Recovery**: If an individual pipeline stage fails (e.g. video has no speech or audio is silent), the job transitions cleanly to `failed` status with a descriptive diagnostic error rather than crashing the backend process.
