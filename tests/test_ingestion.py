"""
Phase 2 Ingestion, Validation & Metadata Extraction Test Suite
"""
import os
import shutil
import pytest
from pathlib import Path
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.core.ingestion import (
    extract_video_metadata,
    validate_video_file,
    generate_thumbnails,
    SUPPORTED_EXTENSIONS,
)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def sample_mp4(tmp_path):
    dest = tmp_path / "sample.mp4"
    if not dest.exists():
        import subprocess
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=4:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(dest)
        ], capture_output=True, check=True)
    return dest

@pytest.fixture
def sample_webm(tmp_path):
    dest = tmp_path / "sample.webm"
    if not dest.exists():
        import subprocess
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=4:size=640x360:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=800:duration=4",
            "-c:v", "libvpx", "-b:v", "500k", "-c:a", "libvorbis",
            str(dest)
        ], capture_output=True, check=True)
    return dest

def test_metadata_extraction_mp4(sample_mp4):
    meta = extract_video_metadata(sample_mp4)
    assert meta.duration >= 3.8
    assert meta.width == 1280
    assert meta.height == 720
    assert meta.fps == 30.0
    assert meta.video_codec == "h264"
    assert meta.has_audio is True
    assert meta.audio_codec == "aac"
    assert meta.aspect_ratio == "16:9"
    assert meta.is_vertical is False

def test_metadata_extraction_webm(sample_webm):
    meta = extract_video_metadata(sample_webm)
    assert meta.duration >= 3.8
    assert meta.width == 640
    assert meta.height == 360
    assert meta.fps == 25.0
    assert meta.video_codec == "vp8"
    assert meta.has_audio is True
    assert meta.aspect_ratio == "16:9"

def test_validation_rejects_non_video(tmp_path):
    fake_txt = tmp_path / "document.txt"
    fake_txt.write_text("Hello world this is not a video")
    with pytest.raises(ValueError, match="Unsupported video format"):
        validate_video_file(fake_txt)

def test_validation_rejects_empty_file(tmp_path):
    empty_mp4 = tmp_path / "empty.mp4"
    empty_mp4.touch()
    with pytest.raises(ValueError, match="empty or corrupted"):
        validate_video_file(empty_mp4)

def test_thumbnail_generation(sample_mp4, tmp_path):
    thumbs_dir = tmp_path / "thumbs"
    thumbs = generate_thumbnails(sample_mp4, thumbs_dir, timestamps=[1.0, 2.0])
    assert len(thumbs) >= 1
    for t in thumbs:
        assert t.exists()
        assert t.stat().st_size > 0

def test_upload_and_stream_workflow(client, sample_mp4):
    # 1. Create project
    proj_res = client.post("/projects", json={"title": "Ingestion Upload Test"})
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]
    
    # 2. Upload video
    with open(sample_mp4, "rb") as f:
        upload_res = client.post(
            f"/projects/{proj_id}/upload",
            files={"file": ("sample.mp4", f, "video/mp4")}
        )
    assert upload_res.status_code == 200
    data = upload_res.json()
    assert data["status"] == "ready"
    assert data["width"] == 1280
    assert data["height"] == 720
    assert data["duration"] >= 3.8
    assert data["codec"] == "h264"
    
    # 3. Retrieve thumbnail
    thumb_res = client.get(f"/projects/{proj_id}/thumbnail")
    assert thumb_res.status_code == 200
    assert thumb_res.headers["content-type"] == "image/jpeg"
    assert len(thumb_res.content) > 0
    
    # 4. Stream video with HTTP Range Request (206)
    stream_res = client.get(
        f"/projects/{proj_id}/stream",
        headers={"Range": "bytes=0-1023"}
    )
    assert stream_res.status_code == 206
    assert "Content-Range" in stream_res.headers
    assert len(stream_res.content) == 1024
    
    # 5. Clean up project
    del_res = client.delete(f"/projects/{proj_id}")
    assert del_res.status_code == 204
