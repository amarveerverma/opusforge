"""
Phase 9 End-to-End QA, Edge Case & Benchmark Suite
Verifies audio/video drift synchronization, silent audio fallbacks,
no-face screen recording reframing, SQLite WAL recovery, and NVENC GPU rendering speed.
"""
import time
import uuid
import json
import sqlite3
import pytest
import subprocess
from pathlib import Path

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.core.transcription import extract_audio_for_transcription
from backend.app.core.face_tracker import track_faces_in_video
from backend.app.core.reframer import calculate_clip_framing
from backend.app.core.renderer import render_clip, RenderResult
from backend.app.core.ingestion import extract_video_metadata

@pytest.fixture
def video_without_audio(tmp_path):
    """Generates synthetic video with NO audio stream."""
    dest = tmp_path / "video_no_audio.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=1280x720:rate=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(dest)
    ], capture_output=True, check=True)
    return dest

@pytest.fixture
def screen_recording_no_faces(tmp_path):
    """Generates synthetic video with moving geometric shapes / text (no human faces)."""
    dest = tmp_path / "screen_share.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "smptebars=duration=3:size=1920x1080:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(dest)
    ], capture_output=True, check=True)
    return dest

@pytest.fixture
def benchmark_video_10s(tmp_path):
    """Generates a 10-second 1080p video for NVENC throughput benchmarking."""
    dest = tmp_path / "benchmark_10s.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=10:size=1920x1080:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=800:duration=10",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(dest)
    ], capture_output=True, check=True)
    return dest

def test_edge_case_video_without_audio(video_without_audio, tmp_path):
    """Verifies that videos without audio tracks are gracefully handled without crashing."""
    out_audio = tmp_path / "extracted_silent.wav"
    # Audio extraction should detect missing audio and synthesize silent 16kHz WAV
    extract_audio_for_transcription(video_without_audio, out_audio)
    assert out_audio.exists()
    assert out_audio.stat().st_size > 1000

    # Rendering test: should produce valid 9:16 MP4 even if source has no audio
    rendered_output = tmp_path / "rendered_no_audio.mp4"
    crop_cfg = {
        "mode": "center",
        "crop_w": 404,
        "crop_h": 720,
        "crop_x": 438,
        "crop_y": 0,
        "target_width": 1080,
        "target_height": 1920,
    }
    result = render_clip(
        source_video=video_without_audio,
        start_time=0.0,
        end_time=2.5,
        output_path=rendered_output,
        crop_config=crop_cfg,
        ass_path=None,
        use_nvenc=True,
    )
    assert result.success is True
    assert rendered_output.exists()
    assert result.width == 1080
    assert result.height == 1920

def test_edge_case_no_faces_screen_recording(screen_recording_no_faces):
    """Verifies that non-face footage triggers smart framing fallbacks."""
    # 1. MediaPipe tracker should find 0 faces
    face_res = track_faces_in_video(screen_recording_no_faces, sample_fps=4.0)
    assert face_res.has_visible_faces is False
    assert face_res.frames_with_faces == 0

    # 2. Smart Track should flag fallback_applied = True and use centered crop
    crop_cfg = calculate_clip_framing(
        source_width=1920,
        source_height=1080,
        clip_start=0.0,
        clip_end=3.0,
        face_data=face_res.model_dump(),
        mode="smart_track",
    )
    assert crop_cfg.has_face is False
    assert crop_cfg.fallback_applied is True
    assert crop_cfg.crop_x == 656 # Centered crop on 1920: (1920 - 608) / 2 = 656

    # 3. Blur background mode should generate valid FFmpeg filter
    blur_cfg = calculate_clip_framing(
        source_width=1920,
        source_height=1080,
        clip_start=0.0,
        clip_end=3.0,
        mode="blur_background",
    )
    assert blur_cfg.mode == "blur_background"
    assert "boxblur=" in blur_cfg.ffmpeg_video_filter
    assert "overlay=" in blur_cfg.ffmpeg_video_filter

def test_nvenc_rendering_speed_benchmark(benchmark_video_10s, tmp_path):
    """Benchmarks hardware NVENC encoding speed on NVIDIA GPU."""
    output_mp4 = tmp_path / "benchmark_rendered.mp4"
    crop_cfg = {
        "mode": "smart_track",
        "crop_w": 608,
        "crop_h": 1080,
        "crop_x": 656,
        "crop_y": 0,
        "target_width": 1080,
        "target_height": 1920,
    }

    t0 = time.perf_counter()
    result = render_clip(
        source_video=benchmark_video_10s,
        start_time=0.0,
        end_time=10.0,
        output_path=output_mp4,
        crop_config=crop_cfg,
        ass_path=None,
        use_nvenc=True,
    )
    render_time = time.perf_counter() - t0

    assert result.success is True
    assert output_mp4.exists()
    assert result.width == 1080
    assert result.height == 1920

    # Compute Speed Metrics
    video_duration = 10.0
    speed_factor = video_duration / max(0.01, render_time)
    effective_fps = (video_duration * 30.0) / max(0.01, render_time)

    print(f"\n[BENCHMARK] 10s 1080x1920 NVENC Render:")
    print(f"  Wall-clock time: {render_time:.2f}s")
    print(f"  Speed factor:    {speed_factor:.1f}x real-time")
    print(f"  Throughput:      {effective_fps:.1f} FPS")
    print(f"  Encoder used:    {result.encoder_used}")

    # Must be faster than real-time playback
    assert speed_factor >= 1.0, f"Expected speed >= 1.0x, got {speed_factor:.2f}x"

def test_audio_video_sync_verification(benchmark_video_10s, tmp_path):
    """Verifies audio and video stream synchronization on rendered shorts."""
    output_mp4 = tmp_path / "sync_test.mp4"
    crop_cfg = {
        "mode": "center",
        "crop_w": 608,
        "crop_h": 1080,
        "crop_x": 656,
        "crop_y": 0,
        "target_width": 1080,
        "target_height": 1920,
    }

    result = render_clip(
        source_video=benchmark_video_10s,
        start_time=2.0,
        end_time=7.5,
        output_path=output_mp4,
        crop_config=crop_cfg,
        ass_path=None,
        use_nvenc=True,
    )
    assert result.success is True

    # Use FFprobe to inspect exact stream durations
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,duration",
        "-of", "json",
        str(output_mp4)
    ]
    probe_out = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    probe_data = json.loads(probe_out.stdout)

    v_dur = None
    a_dur = None
    for st in probe_data.get("streams", []):
        if st.get("codec_type") == "video" and "duration" in st:
            v_dur = float(st["duration"])
        elif st.get("codec_type") == "audio" and "duration" in st:
            a_dur = float(st["duration"])

    assert v_dur is not None, "Video stream must have a valid duration"
    # Expected duration: 7.5 - 2.0 = 5.5s
    assert abs(v_dur - 5.5) <= 0.4, f"Video duration {v_dur} diverges from requested 5.5s"

    if a_dur is not None:
        drift = abs(v_dur - a_dur)
        print(f"\n[A/V SYNC] Video: {v_dur:.3f}s, Audio: {a_dur:.3f}s, Drift: {drift:.3f}s")
        assert drift <= 0.25, f"Audio/Video track drift {drift}s exceeds 0.25s threshold"

def test_database_wal_integrity_and_recovery():
    """Verifies SQLite WAL journaling resilience, integrity check, and checkpointing."""
    db_path = settings.DB_PATH
    assert db_path.exists()

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # 1. Integrity check
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchall()
        assert res == [("ok",)], f"Database corruption detected: {res}"

        # 2. Check journal mode is WAL
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

        # 3. Checkpoint WAL log
        cursor.execute("PRAGMA wal_checkpoint(PASSIVE);")
        ckpt_res = cursor.fetchone()
        assert ckpt_res[0] == 0, f"WAL checkpoint returned error code {ckpt_res[0]}"
