"""
Phase 4 Scene Cuts, Diarization & Face Tracking Test Suite
"""
import os
import json
import pytest
from pathlib import Path
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings
from backend.app.core.scene_detect import detect_scenes, SceneAnalysisResult
from backend.app.core.face_tracker import track_faces_in_video, FaceTrackingResult
from backend.app.core.diarization import diarize_audio, DiarizationResult

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def sample_video_with_scenes(tmp_path):
    """Generates a 6-second video with 2 distinct visual scenes and an audio track."""
    dest = tmp_path / "scenes_test.mp4"
    import subprocess
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:s=640x360:d=3",
        "-f", "lavfi", "-i", "color=c=white:s=640x360:d=3",
        "-f", "lavfi", "-i", "sine=frequency=800:duration=6",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
        "-map", "[outv]",
        "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(dest)
    ], capture_output=True, check=True)
    return dest

def test_scene_detection(sample_video_with_scenes):
    result = detect_scenes(sample_video_with_scenes, threshold=15.0)
    assert isinstance(result, SceneAnalysisResult)
    assert result.total_scenes >= 2
    assert len(result.scenes) >= 2
    for s in result.scenes:
        assert s.start_seconds <= s.end_seconds
        assert s.duration_seconds >= 0.0

def test_face_tracking(sample_video_with_scenes):
    result = track_faces_in_video(sample_video_with_scenes, sample_fps=3.0)
    assert isinstance(result, FaceTrackingResult)
    assert result.total_frames_sampled > 0
    assert 0.0 <= result.average_face_x <= 1.0
    for frame in result.trajectory:
        assert frame.timestamp >= 0.0
        for box in frame.faces:
            assert 0.0 <= box.x <= 1.0
            assert 0.0 <= box.y <= 1.0
            assert 0.0 <= box.w <= 1.0
            assert 0.0 <= box.h <= 1.0

def test_speaker_diarization():
    speech_wav = Path("test_speech.wav")
    assert speech_wav.exists(), "test_speech.wav fixture missing"
    
    result = diarize_audio(speech_wav)
    assert isinstance(result, DiarizationResult)
    assert result.num_speakers >= 1
    assert len(result.segments) >= 1
    assert "visual identity" in result.disclaimer.lower()
    
    for seg in result.segments:
        assert seg.speaker_id.startswith("SPEAKER_")
        assert seg.start <= seg.end
        assert seg.duration > 0

def test_analysis_api_workflow(client, sample_video_with_scenes):
    # 1. Create project
    create_res = client.post("/projects", json={"title": "Analysis API Test"})
    proj_id = create_res.json()["id"]
    
    # 2. Upload video
    with open(sample_video_with_scenes, "rb") as f:
        client.post(f"/projects/{proj_id}/upload", files={"file": ("video.mp4", f, "video/mp4")})
        
    # 3. Trigger Phase 4 analysis
    analysis_res = client.post(f"/projects/{proj_id}/analysis")
    assert analysis_res.status_code == 200
    data = analysis_res.json()
    assert "scenes" in data
    assert "diarization" in data
    assert "faces" in data
    assert data["status"] == "analyzed"
    
    # 4. Fetch stored analysis via GET
    get_res = client.get(f"/projects/{proj_id}/analysis")
    assert get_res.status_code == 200
    stored = get_res.json()
    assert "scenes" in stored
    assert "diarization" in stored
    assert "faces" in stored
    
    # Clean up
    client.delete(f"/projects/{proj_id}")
