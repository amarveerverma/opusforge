# ClipForge — System Architecture

## 1. System Topology

```
┌─────────────────────────────────────────────────────────────┐
│                       Web Browser                           │
│                 Next.js 14/15 Frontend                      │
│                 http://localhost:3000                       │
└──────────────────────────────▲──────────────────────────────┘
                               │
                HTTP REST API  │  Server-Sent Events (SSE)
                JSON Payloads  │  Live Job Progress
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│                 http://localhost:8000                       │
│  - Project & Media Management                               │
│  - SQLite Database Operations                               │
│  - Pipeline Job Orchestrator                                │
│  - Media & Thumbnail Streamer                               │
└──────────────────────────────▲──────────────────────────────┘
                               │
            Sequential In-Process Job Execution
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Local Processing Engine                    │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. Ingestion: FFprobe + OpenCV Frame Extraction       │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              ▼                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 2. Speech: WhisperX / Faster-Whisper (CUDA FP16)     │  │
│  │    --> Word Timestamps & Alignments                   │  │
│  │    --> [Explicit VRAM Eviction & GC]                  │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              ▼                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 3. Audio & Scene: pyannote.audio + PySceneDetect      │  │
│  │    --> Speaker Diarization & Cut Boundaries           │  │
│  │    --> [Explicit VRAM Eviction & GC]                  │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              ▼                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 4. Computer Vision: MediaPipe BlazeFace + Tracking    │  │
│  │    --> Face Trajectories & Smoothing (EMA/Kalman)     │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              ▼                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 5. AI Discovery & Scoring: Hook/Flow/Value Engine     │  │
│  │    --> Local Heuristic Ranker + Optional Cloud LLM    │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              ▼                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 6. Subtitles & Render: ASS Generator + FFmpeg NVENC   │  │
│  │    --> 1080x1920 9:16 MP4 Hardware Encode             │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Local Storage Hierarchy                     │
│  c:\clipper\data\                                           │
│  ├── database/clipforge.db                                  │
│  └── projects/{project_id}/                                 │
│      ├── source/ (Original video, read-only)                │
│      ├── thumbnails/                                        │
│      ├── transcripts/ (JSON + SRT + TXT)                    │
│      ├── analysis/ (Diarization, scenes, face tracks)       │
│      ├── candidates/ (Discovered clip metadata)             │
│      └── renders/ (Exported 9:16 MP4s)                      │
└─────────────────────────────────────────────────────────────┘
```

## 2. Component Decoupling
- **Frontend Independence**: The Next.js frontend is entirely decoupled from Python. It communicates via standardized OpenAPI 3.0 REST endpoints and SSE streams.
- **Worker Isolation**: Video processing jobs execute in background threads/tasks managed by an asynchronous job queue inside FastAPI. Long jobs never block API requests or render the web server unresponsive.
- **Database Architecture**: SQLite with WAL mode (`PRAGMA journal_mode=WAL`) guarantees concurrent read access without database locking conflicts.
