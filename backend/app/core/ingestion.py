"""
ClipForge Video Ingestion, Validation & Metadata Extraction Engine
"""
import os
import json
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import UploadFile

logger = logging.getLogger("clipforge.ingestion")

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}

class VideoMetadata(BaseModel):
    duration: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: Optional[str] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    bitrate: Optional[int] = None
    file_size_bytes: int
    aspect_ratio: str
    has_audio: bool
    is_vertical: bool

def find_ffmpeg_binary(name: str = "ffprobe") -> str:
    """Finds ffprobe or ffmpeg in system PATH or common installation paths."""
    found = shutil.which(name)
    if found:
        return found
    # Fallback check for Gyan.dev Winget package path
    winget_base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for p in winget_base.glob(f"**/{name}.exe"):
        return str(p)
    return name

def extract_video_metadata(file_path: Path) -> VideoMetadata:
    """
    Executes ffprobe to extract comprehensive audio & video stream metadata in JSON.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Video file does not exist: {file_path}")
        
    ffprobe_bin = find_ffmpeg_binary("ffprobe")
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-print_format", "json",
        str(file_path),
    ]
    
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)
    except subprocess.CalledProcessError as e:
        logger.error("FFprobe execution failed: %s", e.stderr)
        raise ValueError(f"Unable to inspect media file. Container may be corrupt: {e.stderr}")
    except json.JSONDecodeError as e:
        logger.error("Failed to parse FFprobe JSON: %s", e)
        raise ValueError(f"Corrupt metadata returned by FFprobe: {e}")
        
    streams = data.get("streams", [])
    fmt = data.get("format", {})
    
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    
    if not video_stream:
        raise ValueError("File contains no valid video streams.")
        
    # Extract dimensions
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid video dimensions: {width}x{height}")
        
    # Calculate aspect ratio
    aspect_ratio = f"{width}:{height}"
    if width > 0 and height > 0:
        ratio = width / height
        if abs(ratio - 16/9) < 0.05:
            aspect_ratio = "16:9"
        elif abs(ratio - 9/16) < 0.05:
            aspect_ratio = "9:16"
        elif abs(ratio - 1.0) < 0.05:
            aspect_ratio = "1:1"
        elif abs(ratio - 4/3) < 0.05:
            aspect_ratio = "4:3"
            
    is_vertical = height > width
    
    # Calculate FPS
    fps_str = video_stream.get("r_frame_rate", "30/1")
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = round(float(num) / float(den), 2)
        else:
            fps = float(fps_str)
    except Exception:
        fps = 30.0
        
    # Duration
    duration = float(fmt.get("duration", 0.0))
    if duration <= 0 and "duration" in video_stream:
        duration = float(video_stream.get("duration", 0.0))
        
    # Bitrate & size
    file_size_bytes = int(fmt.get("size", file_path.stat().st_size))
    bitrate = int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else None
    
    # Audio metadata
    has_audio = audio_stream is not None
    audio_codec = audio_stream.get("codec_name") if audio_stream else None
    audio_sr = int(audio_stream.get("sample_rate", 0)) if audio_stream and "sample_rate" in audio_stream else None
    audio_channels = int(audio_stream.get("channels", 0)) if audio_stream and "channels" in audio_stream else None
    
    return VideoMetadata(
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        video_codec=video_stream.get("codec_name", "unknown"),
        audio_codec=audio_codec,
        audio_sample_rate=audio_sr,
        audio_channels=audio_channels,
        bitrate=bitrate,
        file_size_bytes=file_size_bytes,
        aspect_ratio=aspect_ratio,
        has_audio=has_audio,
        is_vertical=is_vertical,
    )

def validate_video_file(file_path: Path) -> VideoMetadata:
    """
    Validates file format, non-zero size, and reads metadata.
    Raises ValueError with explanatory message on failure.
    """
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")
        
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported video format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        
    if file_path.stat().st_size < 1024:
        raise ValueError("Uploaded file is empty or corrupted (size < 1KB).")
        
    metadata = extract_video_metadata(file_path)
    
    if metadata.duration < 3.0:
        raise ValueError(f"Video is too short ({metadata.duration:.1f}s). Minimum required duration is 3 seconds.")
        
    return metadata

def generate_thumbnails(video_path: Path, output_dir: Path, timestamps: Optional[List[float]] = None) -> List[Path]:
    """
    Generates high-definition thumbnail frames at key timestamps using FFmpeg.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = extract_video_metadata(video_path)
    dur = metadata.duration
    
    if not timestamps:
        # Default sampling timestamps: 10%, 25%, 50%
        timestamps = [
            round(dur * 0.10, 2),
            round(dur * 0.25, 2),
            round(dur * 0.50, 2),
        ]
        # Keep within bounds
        timestamps = [max(0.5, min(t, max(0.5, dur - 0.5))) for t in timestamps]
        
    ffmpeg_bin = find_ffmpeg_binary("ffmpeg")
    generated = []
    
    for idx, ts in enumerate(timestamps):
        out_thumb = output_dir / f"thumb_{idx}.jpg"
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", str(ts),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            "-vf", "scale='min(720,iw)':-1",  # High quality, scaled to max 720p width
            str(out_thumb),
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            if out_thumb.exists() and out_thumb.stat().st_size > 0:
                generated.append(out_thumb)
        except subprocess.CalledProcessError as e:
            logger.warning("Failed to extract thumbnail at %.1fs: %s", ts, e.stderr)
            
    # If no thumbnails succeeded, extract frame 0 as fallback
    if not generated:
        fallback_thumb = output_dir / "thumb_default.jpg"
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "3",
            str(fallback_thumb)
        ]
        subprocess.run(cmd, capture_output=True, check=False)
        if fallback_thumb.exists():
            generated.append(fallback_thumb)
            
    return generated

async def save_upload_stream(upload_file: UploadFile, destination_path: Path, chunk_size: int = 1024 * 1024) -> int:
    """
    Streams uploaded file bytes asynchronously in chunks to disk to prevent RAM bloat.
    """
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    with open(destination_path, "wb") as f:
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            total_bytes += len(chunk)
    return total_bytes
