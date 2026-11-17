"""
Phase 7 Dynamic Captions & Hardware Video Rendering Test Suite
Verifies ASS subtitle generation, karaoke word-level highlighting,
preset aesthetics (MrBeast, Hormozi, Minimalist), FFmpeg 9:16 rendering with NVENC,
and REST API endpoints for rendering and HTTP 206 streaming.
"""
import uuid
import json
import pytest
import subprocess
from pathlib import Path
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.database import get_db
from backend.app.config import settings
from backend.app.core.subtitles import generate_ass_file, PRESETS, format_ass_timestamp
from backend.app.core.renderer import render_clip, RenderResult

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def test_video(tmp_path):
    dest = tmp_path / "test_render_source.mp4"
    if not dest.exists():
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=4:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(dest)
        ], capture_output=True, check=True)
    return dest

def test_ass_generation_and_styling(tmp_path):
    words = [
        {"word": "Why", "start": 0.5, "end": 0.9},
        {"word": "does", "start": 0.9, "end": 1.2},
        {"word": "nobody", "start": 1.2, "end": 1.8},
        {"word": "talk", "start": 1.8, "end": 2.2},
        {"word": "about", "start": 2.2, "end": 2.5},
        {"word": "this", "start": 2.5, "end": 2.8},
        {"word": "secret?", "start": 2.8, "end": 3.4},
    ]

    # 1. Test MrBeast Preset
    mrbeast_ass = tmp_path / "mrbeast.ass"
    generate_ass_file(words, clip_start=0.0, clip_end=4.0, output_path=mrbeast_ass, preset_name="mrbeast")
    assert mrbeast_ass.exists()
    content_mb = mrbeast_ass.read_text(encoding="utf-8")
    assert "PlayResX: 1080" in content_mb
    assert "PlayResY: 1920" in content_mb
    assert "Arial Black" in content_mb
    assert "SECRET?" in content_mb # uppercase check
    assert r"{\c&H0000D4FF&}" in content_mb # MrBeast highlight color
    assert "Dialogue:" in content_mb

    # 2. Test Hormozi Preset
    hormozi_ass = tmp_path / "hormozi.ass"
    generate_ass_file(words, clip_start=0.0, clip_end=4.0, output_path=hormozi_ass, preset_name="hormozi")
    assert hormozi_ass.exists()
    content_hz = hormozi_ass.read_text(encoding="utf-8")
    assert "Impact" in content_hz
    assert r"{\c&H000033FF&}" in content_hz # Hormozi neon red highlight

    # 3. Test Minimalist Preset (lowercase / clean font)
    min_ass = tmp_path / "min.ass"
    generate_ass_file(words, clip_start=0.0, clip_end=4.0, output_path=min_ass, preset_name="minimalist")
    assert min_ass.exists()
    content_min = min_ass.read_text(encoding="utf-8")
    assert "Arial" in content_min
    assert "nobody" in content_min # preserved casing

def test_hardware_rendering_engine(test_video, tmp_path):
    output_mp4 = tmp_path / "output_clip_9x16.mp4"
    ass_path = tmp_path / "test_subs.ass"
    words = [
        {"word": "RENDER", "start": 0.5, "end": 1.5},
        {"word": "TEST", "start": 1.5, "end": 2.5},
    ]
    generate_ass_file(words, clip_start=0.0, clip_end=3.0, output_path=ass_path, preset_name="mrbeast")

    crop_cfg = {
        "mode": "smart_track",
        "crop_w": 404,
        "crop_h": 720,
        "crop_x": 438,
        "crop_y": 0,
        "target_width": 1080,
        "target_height": 1920,
    }

    result = render_clip(
        source_video=test_video,
        start_time=0.5,
        end_time=3.0,
        output_path=output_mp4,
        crop_config=crop_cfg,
        ass_path=ass_path,
        use_nvenc=True,
    )

    assert result.success is True
    assert output_mp4.exists()
    assert result.file_size_bytes > 1024
    assert result.width == 1080
    assert result.height == 1920
    assert result.duration >= 2.0
    assert result.encoder_used in ["h264_nvenc", "libx264"]

def test_rendering_api_lifecycle(client, test_video):
    # 1. Create project
    p_res = client.post("/projects", json={"title": "Render API Project", "instructions": "test"})
    assert p_res.status_code == 201
    proj_id = p_res.json()["id"]

    # Copy test video to project directory
    proj_dir = settings.PROJECTS_DIR / proj_id
    src_dir = proj_dir / "source"
    src_dir.mkdir(parents=True, exist_ok=True)
    proj_video = src_dir / "test_video.mp4"
    import shutil
    shutil.copyfile(test_video, proj_video)

    # 2. Write dummy transcript for subtitle testing
    transcript_dir = proj_dir / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_data = {
        "text": "Hello world welcome to ClipForge local AI clipping.",
        "segments": [
            {
                "start": 0.0,
                "end": 3.0,
                "text": "Hello world welcome to ClipForge local AI clipping.",
                "words": [
                    {"word": "Hello", "start": 0.2, "end": 0.6},
                    {"word": "world", "start": 0.6, "end": 1.0},
                    {"word": "welcome", "start": 1.0, "end": 1.5},
                    {"word": "to", "start": 1.5, "end": 1.7},
                    {"word": "ClipForge", "start": 1.7, "end": 2.5},
                ]
            }
        ]
    }
    (transcript_dir / "transcript.json").write_text(json.dumps(transcript_data), encoding="utf-8")

    # Update project source path in SQLite
    import asyncio
    async def update_project():
        async with get_db() as db:
            await db.execute(
                "UPDATE projects SET source_file_path = ?, width = 1280, height = 720, duration = 4.0 WHERE id = ?",
                (str(proj_video), proj_id)
            )
            await db.commit()
    asyncio.run(update_project())

    # 3. Create clip in SQLite
    clip_id = f"clip_{uuid.uuid4().hex[:8]}"
    crop_cfg = {
        "mode": "smart_track",
        "crop_w": 404,
        "crop_h": 720,
        "crop_x": 438,
        "crop_y": 0,
        "target_width": 1080,
        "target_height": 1920,
    }
    caption_cfg = {"preset": "mrbeast"}

    async def create_clip():
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO clips (
                    id, project_id, rank, start_time, end_time, duration,
                    title, hook, summary, virality_score, letter_grade,
                    crop_config_json, caption_config_json, status
                ) VALUES (?, ?, 1, 0.2, 2.5, 2.3, 'Render Test Clip', 'Hello world', 'Summary', 92.0, 'A+', ?, ?, 'suggested')
                """,
                (clip_id, proj_id, json.dumps(crop_cfg), json.dumps(caption_cfg))
            )
            await db.commit()
    asyncio.run(create_clip())

    # 4. Trigger Render: POST /clips/{clip_id}/render
    render_res = client.post(f"/clips/{clip_id}/render")
    assert render_res.status_code == 200
    render_data = render_res.json()
    assert render_data["clip_id"] == clip_id
    assert render_data["width"] == 1080
    assert render_data["height"] == 1920
    assert render_data["encoder_used"] in ["h264_nvenc", "libx264"]
    render_id = render_data["id"]

    # 5. Check GET /clips/{clip_id}/render
    clip_rnd_res = client.get(f"/clips/{clip_id}/render")
    assert clip_rnd_res.status_code == 200
    assert clip_rnd_res.json()["id"] == render_id

    # 6. Check GET /renders/{render_id}
    rnd_info_res = client.get(f"/renders/{render_id}")
    assert rnd_info_res.status_code == 200
    assert rnd_info_res.json()["id"] == render_id

    # 7. Check HTTP 206 Streaming: GET /renders/{render_id}/stream
    stream_res = client.get(
        f"/renders/{render_id}/stream",
        headers={"Range": "bytes=0-1024"}
    )
    assert stream_res.status_code == 206
    assert "bytes 0-1024/" in stream_res.headers.get("Content-Range", "")
    assert len(stream_res.content) == 1025

    # 8. Check GET /projects/{project_id}/renders
    list_renders_res = client.get(f"/projects/{proj_id}/renders")
    assert list_renders_res.status_code == 200
    assert len(list_renders_res.json()) >= 1
