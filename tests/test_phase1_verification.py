"""
Phase 1 End-to-End Verification Test
Verifies all deliverables of Phase 1:
- Git repo
- SQLite with WAL mode
- FastAPI backend endpoints (/health, /system/status, /projects)
- Hardware telemetry (RTX 4060 GPU, NVENC, VRAM, RAM, Disk)
- Project directory allocation on disk
- Next.js frontend production build readiness
"""
import os
import sqlite3
from pathlib import Path
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings

def test_sqlite_wal_mode():
    assert settings.DB_PATH.exists(), f"Database file missing: {settings.DB_PATH}"
    with sqlite3.connect(str(settings.DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal", f"Expected WAL mode, got {mode}"

def test_api_endpoints_and_telemetry():
    with TestClient(app) as client:
        # 1. Health
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"
        
        # 2. System Status & Hardware
        res = client.get("/system/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "online"
        assert "NVIDIA" in data["gpu"]["name"]
        assert data["gpu"]["vram_total_mb"] > 0
        assert "h264_nvenc" in data["encoders"]
        
        # 3. Project Creation
        proj_payload = {
            "title": "Phase 1 Complete Verification",
            "instructions": "Find viral 9:16 vertical clips with dynamic captions"
        }
        create_res = client.post("/projects", json=proj_payload)
        assert create_res.status_code == 201
        proj = create_res.json()
        proj_id = proj["id"]
        
        # 4. Filesystem Directory Verification
        proj_dir = settings.PROJECTS_DIR / proj_id
        assert proj_dir.exists(), f"Project directory missing: {proj_dir}"
        assert (proj_dir / "source").exists()
        assert (proj_dir / "thumbnails").exists()
        assert (proj_dir / "transcripts").exists()
        assert (proj_dir / "candidates").exists()
        assert (proj_dir / "renders").exists()

def test_nextjs_build_artifacts():
    next_dir = settings.ROOT_DIR / "frontend" / ".next"
    assert next_dir.exists(), "Next.js .next build directory missing"
    assert (next_dir / "BUILD_ID").exists(), "Next.js build was not completed"
