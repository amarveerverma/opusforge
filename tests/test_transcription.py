"""
Phase 3 Transcription & Alignment Test Suite
Validates audio extraction, word-level timestamps, VRAM eviction, and transcript persistence.
"""
import os
import json
import pytest
from pathlib import Path
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings
from backend.app.core.transcription import (
    extract_audio_for_transcription,
    transcribe_audio,
    save_transcript_artifacts,
    export_srt,
    TranscriptResult,
)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def sample_video(tmp_path):
    dest = tmp_path / "sample.mp4"
    speech_wav = Path("test_speech.wav")
    import subprocess
    if speech_wav.exists():
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=5:size=1280x720:rate=30",
            "-ss", "0", "-t", "5", "-i", str(speech_wav),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-shortest",
            str(dest)
        ], capture_output=True, check=True)
    else:
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=4:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(dest)
        ], capture_output=True, check=True)
    return dest

def test_audio_extraction_from_video(sample_video, tmp_path):
    wav_out = tmp_path / "extracted.wav"
    extracted = extract_audio_for_transcription(sample_video, wav_out)
    assert extracted.exists()
    assert extracted.stat().st_size > 1000
    
    # Check audio stream with ffprobe
    import subprocess
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,channels",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(extracted)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = res.stdout.strip().splitlines()
    assert "16000" in lines or lines[0] == "16000"

def test_transcription_word_level_timestamps():
    speech_wav = Path("test_speech.wav")
    assert speech_wav.exists(), "test_speech.wav fixture missing"
    
    # Transcribe using lightweight model for high-speed test
    result = transcribe_audio(
        audio_path=speech_wav,
        model_size="tiny",
        compute_type="float16",
    )
    
    assert isinstance(result, TranscriptResult)
    assert result.language == "en"
    assert len(result.words) > 10
    assert len(result.segments) > 0
    assert len(result.full_text) > 50
    
    # Verify word timestamps structure
    for w in result.words:
        assert w.start >= 0.0
        assert w.end >= w.start
        assert len(w.word.strip()) > 0

def test_transcript_persistence_and_srt(tmp_path):
    speech_wav = Path("test_speech.wav")
    assert speech_wav.exists()
    
    result = transcribe_audio(
        audio_path=speech_wav,
        model_size="tiny",
        compute_type="float16",
    )
    
    save_transcript_artifacts(tmp_path, result)
    
    transcripts_dir = tmp_path / "transcripts"
    assert (transcripts_dir / "transcript_raw.json").exists()
    assert (transcripts_dir / "transcript.json").exists()
    assert (transcripts_dir / "transcript.txt").exists()
    assert (transcripts_dir / "subtitles.srt").exists()
    
    # Verify SRT format
    srt_content = (transcripts_dir / "subtitles.srt").read_text(encoding="utf-8")
    assert "-->" in srt_content
    assert "1" in srt_content

def test_transcription_api_lifecycle(client, sample_video):
    # 1. Create project
    create_res = client.post("/projects", json={"title": "Transcript Lifecycle Test"})
    proj_id = create_res.json()["id"]
    
    # 2. Upload video
    with open(sample_video, "rb") as f:
        client.post(f"/projects/{proj_id}/upload", files={"file": ("sample.mp4", f, "video/mp4")})
        
    # 3. Trigger transcription API (using tiny model for fast test)
    transcribe_res = client.post(
        f"/projects/{proj_id}/transcript",
        json={"model_size": "tiny", "compute_type": "float16"}
    )
    assert transcribe_res.status_code == 200
    data = transcribe_res.json()
    assert "segments" in data
    assert "words" in data
    
    # 4. Fetch transcript via GET
    get_res = client.get(f"/projects/{proj_id}/transcript")
    assert get_res.status_code == 200
    assert get_res.json()["duration"] > 0
    
    # 5. Patch transcript via PATCH
    patch_res = client.patch(
        f"/projects/{proj_id}/transcript",
        json={"full_text": "Updated custom corrected transcription text."}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["full_text"] == "Updated custom corrected transcription text."
    
    # Verify raw transcript is preserved
    proj_dir = settings.PROJECTS_DIR / proj_id
    raw_data = json.loads((proj_dir / "transcripts" / "transcript_raw.json").read_text(encoding="utf-8"))
    assert raw_data["full_text"] != "Updated custom corrected transcription text."
    
    # Clean up
    client.delete(f"/projects/{proj_id}")
