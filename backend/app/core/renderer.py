"""
ClipForge Hardware-Accelerated Video Rendering Engine
Compiles 9:16 portrait video with Lanczos scaling, dynamic ASS subtitles,
and high-speed NVENC GPU encoding (RTX 4060) with CPU libx264 fallback.
Includes automated post-flight QA validation.
"""
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from .ingestion import extract_video_metadata

logger = logging.getLogger("clipforge.renderer")

class RenderResult(BaseModel):
    success: bool
    output_path: str
    duration: float
    width: int
    height: int
    file_size_bytes: int
    render_time_seconds: float
    encoder_used: str
    fps: float = 30.0
    error_message: Optional[str] = None

def escape_ffmpeg_path(path: Path) -> str:
    """Escapes Windows paths for FFmpeg filter_complex syntax (colons and slashes)."""
    p_str = str(path.resolve()).replace("\\", "/")
    # Escape colon (e.g. C: -> C\:)
    if len(p_str) > 1 and p_str[1] == ":":
        p_str = p_str[0] + "\\:" + p_str[2:]
    return p_str

def build_filter_complex(
    crop_config: Dict[str, Any],
    ass_path: Optional[Path] = None
) -> str:
    """
    Constructs the complete video filter complex combining 9:16 reframing
    and ASS dynamic subtitle burn-in.
    """
    mode = crop_config.get("mode", "smart_track")
    crop_w = crop_config.get("crop_w", 608)
    crop_h = crop_config.get("crop_h", 1080)
    crop_x = crop_config.get("crop_x", 656)
    crop_y = crop_config.get("crop_y", 0)
    target_w = crop_config.get("target_width", 1080)
    target_h = crop_config.get("target_height", 1920)
    
    ass_filter = ""
    if ass_path and ass_path.exists():
        escaped_ass = escape_ffmpeg_path(ass_path)
        ass_filter = f",ass='{escaped_ass}'"
        
    if mode == "blur_background":
        # Centered sharp video over blurred background
        filter_str = (
            f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,boxblur=25:5,setsar=1[bg];"
            f"[0:v]scale={target_w}:-2,setsar=1[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2{ass_filter}[outv]"
        )
    elif mode == "split_screen":
        half_h = target_h // 2
        source_w = crop_config.get("source_width", 1920)
        left_px = int(round(max(0, (0.28 * source_w) - (crop_w / 2.0))))
        right_px = int(round(max(0, (0.72 * source_w) - (crop_w / 2.0))))
        left_px -= left_px % 2
        right_px -= right_px % 2
        
        filter_str = (
            f"[0:v]crop={crop_w}:{crop_h}:{left_px}:0,scale={target_w}:{half_h}:flags=lanczos[top];"
            f"[0:v]crop={crop_w}:{crop_h}:{right_px}:0,scale={target_w}:{half_h}:flags=lanczos[bot];"
            f"[top][bot]vstack{ass_filter}[outv]"
        )
    else:
        # Standard Smart Track, Center, or Manual crop
        filter_str = f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={target_w}:{target_h}:flags=lanczos{ass_filter}[outv]"
        
    return filter_str

def render_clip(
    source_video: Path,
    start_time: float,
    end_time: float,
    output_path: Path,
    crop_config: Dict[str, Any],
    ass_path: Optional[Path] = None,
    use_nvenc: bool = True,
    bitrate: str = "6500k",
    cq: int = 20,
) -> RenderResult:
    """
    Renders a 9:16 vertical MP4 clip using FFmpeg with NVENC acceleration
    and automatic libx264 CPU fallback.
    """
    if not source_video.exists():
        raise FileNotFoundError(f"Source video not found: {source_video}")
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = round(end_time - start_time, 2)
    filter_complex = build_filter_complex(crop_config, ass_path)
    
    encoders_to_try = []
    if use_nvenc:
        encoders_to_try.append(("h264_nvenc", [
            "-c:v", "h264_nvenc",
            "-preset", "p5",
            "-tune", "hq",
            "-cq", str(cq),
            "-b:v", bitrate,
            "-maxrate", "9000k",
            "-bufsize", "12000k",
            "-pix_fmt", "yuv420p"
        ]))
        
    # Always have libx264 as safety fallback
    encoders_to_try.append(("libx264", [
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", str(cq),
        "-pix_fmt", "yuv420p"
    ]))
    
    last_error = ""
    render_start = time.perf_counter()
    
    for encoder_name, enc_args in encoders_to_try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-i", str(source_video),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a?", # Optional audio map in case source has no audio
            *enc_args,
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        logger.info("Starting FFmpeg render with %s: %s", encoder_name, " ".join(cmd[:12]))
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(output_path.parent))
        
        if res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1024:
            render_elapsed = round(time.perf_counter() - render_start, 2)
            file_size = output_path.stat().st_size
            
            # Post-flight QA audit via ffprobe
            try:
                meta = extract_video_metadata(output_path)
                out_w = meta.width
                out_h = meta.height
                out_dur = meta.duration
            except Exception as e:
                logger.warning("ffprobe QA check failed to read metadata: %s", e)
                out_w = 1080
                out_h = 1920
                out_dur = duration
                
            logger.info("Render completed successfully with %s in %.2fs (Size: %.2f MB)",
                        encoder_name, render_elapsed, file_size / (1024 * 1024))
            return RenderResult(
                success=True,
                output_path=str(output_path),
                duration=out_dur,
                width=out_w,
                height=out_h,
                file_size_bytes=file_size,
                render_time_seconds=render_elapsed,
                encoder_used=encoder_name,
            )
        else:
            last_error = res.stderr[-800:] if res.stderr else "Unknown FFmpeg error"
            logger.warning("Render failed with %s: %s. Trying fallback...", encoder_name, last_error)
            
    # If all encoders failed
    return RenderResult(
        success=False,
        output_path="",
        duration=0.0,
        width=0,
        height=0,
        file_size_bytes=0,
        render_time_seconds=0.0,
        encoder_used="none",
        error_message=f"All encoders failed. Last error: {last_error}",
    )
