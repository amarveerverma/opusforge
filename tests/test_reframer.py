"""
Phase 6 Smart Vertical Reframing Test Suite
Verifies 9:16 aspect ratio cropping, EMA smoothing with deadband,
fallback framing (blurred background), split-screen, and framing API endpoints.
"""
import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.core.reframer import (
    calculate_crop_dimensions,
    smooth_face_trajectory,
    calculate_clip_framing,
    generate_blur_background_filter,
    generate_split_screen_filter,
    CropConfig,
)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_crop_dimensions_various_resolutions():
    # 1. 1080p Landscape (1920x1080) -> 9:16 requires 607.5px -> 608px even
    w, h = calculate_crop_dimensions(1920, 1080)
    assert h == 1080
    assert w == 608
    assert w % 2 == 0 and h % 2 == 0
    assert abs((w / h) - (9 / 16)) < 0.01

    # 2. 4K Landscape (3840x2160) -> 9:16 requires 1215px -> 1214px even
    w_4k, h_4k = calculate_crop_dimensions(3840, 2160)
    assert h_4k == 2160
    assert w_4k == 1214
    assert w_4k % 2 == 0 and h_4k % 2 == 0

    # 3. 720p Landscape (1280x720) -> 9:16 requires 405px -> 404px even
    w_720, h_720 = calculate_crop_dimensions(1280, 720)
    assert h_720 == 720
    assert w_720 == 404
    assert w_720 % 2 == 0 and h_720 % 2 == 0

    # 4. Native Vertical 9:16 (1080x1920)
    w_vert, h_vert = calculate_crop_dimensions(1080, 1920)
    assert w_vert == 1080
    assert h_vert == 1920

    # 5. Square Video (1080x1080)
    w_sq, h_sq = calculate_crop_dimensions(1080, 1080)
    assert h_sq == 1080
    assert w_sq == 608

def test_ema_smoothing_and_deadband():
    # Small jitter within 5% deadband should NOT move the camera
    jitter_points = [
        (0.0, 0.50),
        (0.5, 0.52), # delta = 0.02 (< 0.05)
        (1.0, 0.48), # delta = 0.02 (< 0.05)
        (1.5, 0.51), # delta = 0.01 (< 0.05)
    ]
    smoothed_jitter = smooth_face_trajectory(jitter_points, alpha=0.1, deadband=0.05)
    # Since initial point is 0.50 and subsequent points stay within 0.05 delta, smooth stays 0.50
    for t, val in smoothed_jitter:
        assert val == 0.50

    # Large camera shift beyond deadband triggers smooth progressive panning
    panning_points = [
        (0.0, 0.50),
        (0.5, 0.75), # delta = 0.25 (> 0.05)
        (1.0, 0.75),
        (1.5, 0.75),
    ]
    smoothed_pan = smooth_face_trajectory(panning_points, alpha=0.2, deadband=0.05)
    vals = [v for _, v in smoothed_pan]
    # Check that it moves gradually towards 0.75
    assert vals[0] == 0.50
    assert vals[1] > vals[0]
    assert vals[2] > vals[1]
    assert vals[3] > vals[2]
    assert vals[3] <= 0.75

def test_smart_tracking_and_fallbacks():
    # Synthetic face trajectory where speaker is on the left third (x ~ 0.30)
    face_data = {
        "has_visible_faces": True,
        "average_face_x": 0.30,
        "trajectory": [
            {"timestamp": 10.0, "primary_center_x": 0.30, "faces": [{"confidence": 0.9}]},
            {"timestamp": 12.0, "primary_center_x": 0.32, "faces": [{"confidence": 0.92}]},
            {"timestamp": 14.0, "primary_center_x": 0.29, "faces": [{"confidence": 0.88}]},
        ]
    }
    
    # 1. Smart Track with faces
    cfg = calculate_clip_framing(
        source_width=1920,
        source_height=1080,
        clip_start=10.0,
        clip_end=15.0,
        face_data=face_data,
        mode="smart_track",
    )
    assert cfg.crop_w == 608
    assert cfg.crop_h == 1080
    assert cfg.has_face is True
    assert cfg.fallback_applied is False
    # Center around x=0.30 * 1920 = 576. Crop width 608 centered at 576 => x = 576 - 304 = 272
    assert abs(cfg.crop_x - 272) < 30
    assert "crop=608:1080" in cfg.ffmpeg_video_filter
    assert "scale=1080:1920" in cfg.ffmpeg_video_filter

    # 2. Smart Track with NO faces detected (Fallback triggered)
    empty_face_data = {"has_visible_faces": False, "average_face_x": 0.5, "trajectory": []}
    cfg_fallback = calculate_clip_framing(
        source_width=1920,
        source_height=1080,
        clip_start=10.0,
        clip_end=15.0,
        face_data=empty_face_data,
        mode="smart_track",
    )
    assert cfg_fallback.has_face is False
    assert cfg_fallback.fallback_applied is True
    # Falls back to centered crop (1920 - 608) / 2 = 656
    assert cfg_fallback.crop_x == 656

    # 3. Blur Background Mode
    cfg_blur = calculate_clip_framing(
        source_width=1920,
        source_height=1080,
        clip_start=10.0,
        clip_end=15.0,
        mode="blur_background",
    )
    assert cfg_blur.mode == "blur_background"
    assert "boxblur=" in cfg_blur.ffmpeg_video_filter
    assert "overlay=" in cfg_blur.ffmpeg_video_filter

    # 4. Split Screen Mode
    cfg_split = calculate_clip_framing(
        source_width=1920,
        source_height=1080,
        clip_start=10.0,
        clip_end=15.0,
        mode="split_screen",
    )
    assert cfg_split.mode == "split_screen"
    assert "vstack" in cfg_split.ffmpeg_video_filter

def test_framing_api_endpoints(client):
    import uuid
    # Create test project
    res = client.post("/projects", json={"title": "Reframing Test Project", "instructions": "test"})
    assert res.status_code == 201
    proj_id = res.json()["id"]
    test_clip_id = f"clip_{uuid.uuid4().hex[:8]}"

    # Insert a dummy clip
    import asyncio
    from backend.app.database import get_db
    import json
    
    async def create_clip():
        async with get_db() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO clips (
                    id, project_id, rank, start_time, end_time, duration,
                    title, hook, summary, virality_score, letter_grade, status
                ) VALUES (?, ?, 1, 5.0, 35.0, 30.0, 'Test Clip', 'Hook', 'Summary', 88.0, 'A', 'suggested')
                """,
                (test_clip_id, proj_id)
            )
            await db.commit()
            
    asyncio.run(create_clip())

    # 1. GET /clips/{id}/framing
    get_res = client.get(f"/clips/{test_clip_id}/framing")
    assert get_res.status_code == 200
    framing = get_res.json()
    assert framing["crop_w"] == 608
    assert framing["crop_h"] == 1080
    assert framing["target_width"] == 1080
    assert framing["target_height"] == 1920

    # 2. PATCH /clips/{id}/framing (switch to blur_background)
    patch_res = client.patch(
        f"/clips/{test_clip_id}/framing",
        json={"mode": "blur_background"}
    )
    assert patch_res.status_code == 200
    updated_blur = patch_res.json()
    assert updated_blur["mode"] == "blur_background"
    assert "boxblur" in updated_blur["ffmpeg_video_filter"]

    # 3. PATCH /clips/{id}/framing (adjust manual focal offset to 0.75)
    patch_res2 = client.patch(
        f"/clips/{test_clip_id}/framing",
        json={"mode": "manual", "manual_x_offset": 0.75}
    )
    assert patch_res2.status_code == 200
    updated_manual = patch_res2.json()
    assert updated_manual["mode"] == "manual"
    assert updated_manual["manual_x_offset"] == 0.75
    # Focal center = 0.75 * 1920 = 1440. Max x = 1920 - 608 = 1312.
    # 1440 - 304 = 1136
    assert abs(updated_manual["crop_x"] - 1136) <= 2
