import os
import re
import subprocess
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
import cv2

from clipper.config import TEMP_DIR, ensure_dirs


class VideoMetadata(BaseModel):
    source_type: str  # "youtube" or "local"
    source_uri: str
    file_path: str
    title: str
    duration: float  # seconds
    fps: float
    width: int
    height: int
    has_audio: bool


def is_youtube_url(url: str) -> bool:
    """Check if input string is a valid YouTube URL."""
    youtube_regex = (
        r"(https?://)?(www\.)?"
        r"(youtube|youtu|youtube-nocookie)\.(com|be)/"
        r"(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
    )
    return bool(re.match(youtube_regex, url.strip()))


def get_video_info_from_file(file_path: Path, title: Optional[str] = None) -> VideoMetadata:
    """Extract metadata from local video file using OpenCV and ffprobe."""
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found at: {file_path}")

    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {file_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = frame_count / fps if fps > 0 and frame_count > 0 else 0.0
    cap.release()

    # If duration could not be reliably determined via OpenCV, probe with ffprobe
    has_audio = True
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration:stream=codec_type",
            "-of", "json",
            str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        info = json.loads(result.stdout)
        if "format" in info and "duration" in info["format"]:
            duration = float(info["format"]["duration"])
        streams = info.get("streams", [])
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
    except Exception:
        pass

    return VideoMetadata(
        source_type="local",
        source_uri=str(file_path),
        file_path=str(file_path.resolve()),
        title=title or file_path.stem,
        duration=round(duration, 2),
        fps=round(fps, 2),
        width=width,
        height=height,
        has_audio=has_audio
    )


def download_youtube_video(url: str, output_dir: Optional[Path] = None) -> VideoMetadata:
    """Download video from YouTube URL using yt-dlp."""
    import yt_dlp

    ensure_dirs()
    target_dir = output_dir or TEMP_DIR

    # Format template
    outtmpl = str(target_dir / "%(id)s_%(title).50s.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": True,
        "noplaylist": True,
        "js_runtimes": {"node": {}},
    }

    # Support optional cookies.txt for age-restricted / member-only videos
    cookies_path = Path("cookies.txt")
    if not cookies_path.exists():
        from clipper.config import BASE_DIR
        cookies_path = BASE_DIR / "cookies.txt"

    if cookies_path.exists():
        print(f"[*] Using YouTube cookies file: {cookies_path.resolve()}")
        ydl_opts["cookiefile"] = str(cookies_path)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_file = Path(ydl.prepare_filename(info_dict))
            
            # In case the extension changed upon merging
            if not downloaded_file.exists():
                mp4_file = downloaded_file.with_suffix(".mp4")
                if mp4_file.exists():
                    downloaded_file = mp4_file

            title = info_dict.get("title", "YouTube Video")
            duration = float(info_dict.get("duration", 0.0))
    except Exception as e:
        err_msg = str(e)
        if "Sign in to confirm your age" in err_msg or "age-restricted" in err_msg.lower():
            raise RuntimeError(
                "This video is Age-Restricted (18+) on YouTube and requires sign-in verification. "
                "Solutions:\n"
                "1. Export your YouTube cookies using a browser extension (like 'Get cookies.txt LOCALLY') "
                "and save it as 'cookies.txt' in the project folder.\n"
                "2. Or test with any standard public YouTube video (e.g. podcast, tutorial, talk).\n"
                "3. Or download the video locally and input the local file path (e.g. C:\\videos\\clip.mp4)."
            )
        raise RuntimeError(f"YouTube download failed: {err_msg}")

    meta = get_video_info_from_file(downloaded_file, title=title)
    meta.source_type = "youtube"
    meta.source_uri = url
    if duration > 0:
        meta.duration = round(duration, 2)
    return meta


def ingest_video(input_source: str, output_dir: Optional[Path] = None) -> VideoMetadata:
    """
    Ingest either a YouTube URL or a local file path.
    Returns standard VideoMetadata.
    """
    input_str = input_source.strip().strip('"').strip("'")
    if is_youtube_url(input_str):
        print(f"[*] Detected YouTube URL. Downloading via yt-dlp: {input_str}")
        return download_youtube_video(input_str, output_dir=output_dir)
    else:
        path = Path(input_str)
        if not path.is_file():
            raise FileNotFoundError(f"Input is neither a valid YouTube URL nor an existing file: {input_source}")
        print(f"[*] Detected local video file: {path.name}")
        return get_video_info_from_file(path)
