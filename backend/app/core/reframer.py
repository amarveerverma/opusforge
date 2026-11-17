"""
ClipForge Smart Vertical Reframing Engine (16:9 to 9:16)
Calculates subject-aware portrait crops, EMA smoothing with deadbands,
rule-of-thirds headroom, and fallback framing (blurred background & split-screen).
"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("clipforge.reframer")

class CropKeyframe(BaseModel):
    timestamp: float
    x: int
    y: int
    w: int
    h: int
    center_x_norm: float

class CropConfig(BaseModel):
    mode: str = Field(..., description="smart_track | center | blur_background | split_screen | manual")
    source_width: int
    source_height: int
    target_width: int = 1080
    target_height: int = 1920
    crop_w: int
    crop_h: int
    crop_x: int
    crop_y: int
    manual_x_offset: Optional[float] = None
    has_face: bool = True
    face_confidence: float = 1.0
    fallback_applied: bool = False
    fallback_reason: Optional[str] = None
    keyframes: List[CropKeyframe] = []
    ffmpeg_video_filter: str

def calculate_crop_dimensions(
    source_width: int,
    source_height: int,
    target_w: int = 1080,
    target_h: int = 1920
) -> Tuple[int, int]:
    """
    Computes optimal crop width and height in source coordinate space
    to match the target aspect ratio (9:16) with even dimensions.
    """
    target_aspect = target_w / target_h  # 9/16 = 0.5625
    source_aspect = source_width / source_height
    
    if source_aspect >= target_aspect:
        # Landscape or wider: use full height, crop horizontal width
        crop_h = source_height
        crop_w = int(round(source_height * target_aspect))
    else:
        # Taller than target aspect: use full width, crop vertical height
        crop_w = source_width
        crop_h = int(round(source_width / target_aspect))
        
    # Guarantee even pixel dimensions for encoder compatibility
    crop_w = crop_w - (crop_w % 2)
    crop_h = crop_h - (crop_h % 2)
    
    # Boundary guard
    crop_w = min(crop_w, source_width)
    crop_h = min(crop_h, source_height)
    
    return crop_w, crop_h

def smooth_face_trajectory(
    raw_points: List[Tuple[float, float]],
    alpha: float = 0.08,
    deadband: float = 0.05,
    default_center: float = 0.5
) -> List[Tuple[float, float]]:
    """
    Applies Exponential Moving Average (EMA) with a deadband threshold to prevent micro-jitter.
    raw_points: List of (timestamp, normalized_x_center)
    Returns: List of (timestamp, smoothed_normalized_x)
    """
    if not raw_points:
        return []
        
    smoothed: List[Tuple[float, float]] = []
    current_smooth = raw_points[0][1] if raw_points else default_center
    
    for t, target_x in raw_points:
        # Only pan camera if target shifts beyond deadband (e.g. 5% screen width)
        delta = abs(target_x - current_smooth)
        if delta > deadband:
            current_smooth = (alpha * target_x) + ((1.0 - alpha) * current_smooth)
            
        current_smooth = max(0.0, min(1.0, current_smooth))
        smoothed.append((t, round(current_smooth, 4)))
        
    return smoothed

def generate_blur_background_filter(
    source_width: int,
    source_height: int,
    target_w: int = 1080,
    target_h: int = 1920,
    blur_strength: int = 25
) -> str:
    """
    Generates an FFmpeg filter complex that centers the landscape video
    over a scaled and blurred copy of itself.
    """
    return (
        f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,boxblur={blur_strength}:5,setsar=1[bg];"
        f"[0:v]scale={target_w}:-2,setsar=1[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
    )

def generate_split_screen_filter(
    source_width: int,
    source_height: int,
    left_x: int,
    right_x: int,
    crop_w: int,
    crop_h: int,
    target_w: int = 1080,
    target_h: int = 1920
) -> str:
    """
    Generates an FFmpeg filter complex for 2-speaker split screen:
    Speaker 1 (top half: 1080x960), Speaker 2 (bottom half: 1080x960).
    """
    half_h = target_h // 2
    return (
        f"[0:v]crop={crop_w}:{crop_h}:{left_x}:0,scale={target_w}:{half_h}:flags=lanczos[top];"
        f"[0:v]crop={crop_w}:{crop_h}:{right_x}:0,scale={target_w}:{half_h}:flags=lanczos[bot];"
        f"[top][bot]vstack[outv]"
    )

def calculate_clip_framing(
    source_width: int,
    source_height: int,
    clip_start: float,
    clip_end: float,
    face_data: Optional[Dict[str, Any]] = None,
    mode: str = "smart_track",
    manual_x_offset: Optional[float] = None,
    target_w: int = 1080,
    target_h: int = 1920,
    headroom_factor: float = 0.33,
    deadband_pct: float = 0.05,
    alpha: float = 0.08
) -> CropConfig:
    """
    Core Reframing Engine:
    Determines 9:16 crop boundaries, keyframe trajectories, and FFmpeg filter directives.
    """
    crop_w, crop_h = calculate_crop_dimensions(source_width, source_height, target_w, target_h)
    max_x = max(0, source_width - crop_w)
    max_y = max(0, source_height - crop_h)
    
    # Vertical placement (Rule of thirds headroom)
    # Default to center vertically if there's spare vertical space
    crop_y = max(0, min(max_y, int(round((source_height - crop_h) * headroom_factor))))
    
    # 1. Mode: BLUR BACKGROUND (No face / Screen Share fallback)
    if mode == "blur_background":
        filter_str = generate_blur_background_filter(source_width, source_height, target_w, target_h)
        return CropConfig(
            mode="blur_background",
            source_width=source_width,
            source_height=source_height,
            target_width=target_w,
            target_height=target_h,
            crop_w=crop_w,
            crop_h=crop_h,
            crop_x=int(round(max_x / 2)),
            crop_y=crop_y,
            manual_x_offset=manual_x_offset,
            has_face=False,
            face_confidence=0.0,
            fallback_applied=False,
            keyframes=[],
            ffmpeg_video_filter=filter_str,
        )

    # 2. Mode: MANUAL OFFSET
    if mode == "manual" and manual_x_offset is not None:
        target_center_x = max(0.0, min(1.0, float(manual_x_offset)))
        target_px = target_center_x * source_width
        crop_x = int(round(max(0, min(max_x, target_px - (crop_w / 2.0)))))
        crop_x = crop_x - (crop_x % 2) # ensure even
        filter_str = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={target_w}:{target_h}:flags=lanczos"
        
        return CropConfig(
            mode="manual",
            source_width=source_width,
            source_height=source_height,
            target_width=target_w,
            target_height=target_h,
            crop_w=crop_w,
            crop_h=crop_h,
            crop_x=crop_x,
            crop_y=crop_y,
            manual_x_offset=target_center_x,
            has_face=True,
            face_confidence=1.0,
            fallback_applied=False,
            keyframes=[CropKeyframe(timestamp=clip_start, x=crop_x, y=crop_y, w=crop_w, h=crop_h, center_x_norm=target_center_x)],
            ffmpeg_video_filter=filter_str,
        )

    # 3. Mode: CENTER CROP
    if mode == "center":
        crop_x = int(round(max_x / 2.0))
        crop_x = crop_x - (crop_x % 2)
        filter_str = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={target_w}:{target_h}:flags=lanczos"
        return CropConfig(
            mode="center",
            source_width=source_width,
            source_height=source_height,
            target_width=target_w,
            target_height=target_h,
            crop_w=crop_w,
            crop_h=crop_h,
            crop_x=crop_x,
            crop_y=crop_y,
            manual_x_offset=0.5,
            has_face=False,
            face_confidence=0.0,
            fallback_applied=False,
            keyframes=[CropKeyframe(timestamp=clip_start, x=crop_x, y=crop_y, w=crop_w, h=crop_h, center_x_norm=0.5)],
            ffmpeg_video_filter=filter_str,
        )

    # 4. Mode: SPLIT SCREEN (Two speakers)
    if mode == "split_screen":
        left_center_x = 0.28
        right_center_x = 0.72
        left_px = int(round(max(0, min(max_x, (left_center_x * source_width) - (crop_w / 2.0)))))
        right_px = int(round(max(0, min(max_x, (right_center_x * source_width) - (crop_w / 2.0)))))
        left_px = left_px - (left_px % 2)
        right_px = right_px - (right_px % 2)
        
        filter_str = generate_split_screen_filter(source_width, source_height, left_px, right_px, crop_w, crop_h, target_w, target_h)
        return CropConfig(
            mode="split_screen",
            source_width=source_width,
            source_height=source_height,
            target_width=target_w,
            target_height=target_h,
            crop_w=crop_w,
            crop_h=crop_h,
            crop_x=left_px,
            crop_y=crop_y,
            manual_x_offset=None,
            has_face=True,
            face_confidence=1.0,
            fallback_applied=False,
            keyframes=[],
            ffmpeg_video_filter=filter_str,
        )

    # 5. Mode: SMART TRACK (MediaPipe trajectory + EMA smoothing)
    trajectory_frames = []
    if face_data and "trajectory" in face_data:
        trajectory_frames = face_data["trajectory"]
        
    # Extract face centers within [clip_start, clip_end]
    clip_points: List[Tuple[float, float]] = []
    confidences: List[float] = []
    
    for f in trajectory_frames:
        t = f.get("timestamp", 0.0)
        if clip_start - 0.5 <= t <= clip_end + 0.5:
            cx = f.get("primary_center_x")
            if cx is not None:
                clip_points.append((t, cx))
                faces = f.get("faces", [])
                if faces:
                    confidences.append(faces[0].get("confidence", 0.8))
                    
    # FALLBACK CHECK: If no face coordinates detected in clip
    if not clip_points:
        fallback_reason = "No human face detected during clip window. Fallback to center framing."
        logger.info("Reframer: %s", fallback_reason)
        crop_x = int(round(max_x / 2.0))
        crop_x = crop_x - (crop_x % 2)
        filter_str = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={target_w}:{target_h}:flags=lanczos"
        
        return CropConfig(
            mode="smart_track",
            source_width=source_width,
            source_height=source_height,
            target_width=target_w,
            target_height=target_h,
            crop_w=crop_w,
            crop_h=crop_h,
            crop_x=crop_x,
            crop_y=crop_y,
            manual_x_offset=0.5,
            has_face=False,
            face_confidence=0.0,
            fallback_applied=True,
            fallback_reason=fallback_reason,
            keyframes=[CropKeyframe(timestamp=clip_start, x=crop_x, y=crop_y, w=crop_w, h=crop_h, center_x_norm=0.5)],
            ffmpeg_video_filter=filter_str,
        )

    # Smooth the points with EMA & deadband
    smoothed = smooth_face_trajectory(
        clip_points,
        alpha=alpha,
        deadband=deadband_pct,
        default_center=face_data.get("average_face_x", 0.5) if face_data else 0.5
    )
    
    keyframes: List[CropKeyframe] = []
    x_positions: List[int] = []
    
    for t, smooth_cx in smoothed:
        # Convert normalized center to top-left crop pixel
        target_center_px = smooth_cx * source_width
        px = int(round(max(0, min(max_x, target_center_px - (crop_w / 2.0)))))
        px = px - (px % 2)
        x_positions.append(px)
        keyframes.append(CropKeyframe(
            timestamp=round(t, 2),
            x=px,
            y=crop_y,
            w=crop_w,
            h=crop_h,
            center_x_norm=smooth_cx
        ))
        
    # Representative static crop (median X of smoothed trajectory to prevent jump cuts)
    representative_x = int(round(float(np.median(x_positions)))) if x_positions else int(round(max_x / 2.0))
    representative_x = representative_x - (representative_x % 2)
    representative_x = max(0, min(max_x, representative_x))
    
    avg_conf = round(float(np.mean(confidences)), 2) if confidences else 0.85
    filter_str = f"crop={crop_w}:{crop_h}:{representative_x}:{crop_y},scale={target_w}:{target_h}:flags=lanczos"
    
    return CropConfig(
        mode="smart_track",
        source_width=source_width,
        source_height=source_height,
        target_width=target_w,
        target_height=target_h,
        crop_w=crop_w,
        crop_h=crop_h,
        crop_x=representative_x,
        crop_y=crop_y,
        manual_x_offset=round(float(np.median([p[1] for p in smoothed])), 3) if smoothed else 0.5,
        has_face=True,
        face_confidence=avg_conf,
        fallback_applied=False,
        keyframes=keyframes,
        ffmpeg_video_filter=filter_str,
    )
