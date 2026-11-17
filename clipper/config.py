import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

# Clipper directories
OUTPUT_DIR = Path(os.getenv("CLIPPER_OUTPUT_DIR", str(BASE_DIR / "output")))
TEMP_DIR = Path(os.getenv("CLIPPER_TEMP_DIR", str(BASE_DIR / "temp")))

# Default configuration settings
DEFAULT_CONFIG = {
    "whisper_model": os.getenv("WHISPER_MODEL", "base"),
    "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
    "clip_min_duration": float(os.getenv("CLIP_MIN_DURATION", 15.0)),
    "clip_max_duration": float(os.getenv("CLIP_MAX_DURATION", 90.0)),
    "frame_sample_interval": 2.0,  # seconds
    "target_aspect_ratio": (9, 16),
    "target_width": 1080,
    "target_height": 1920,
    "top_n_clips": 3,
}

def ensure_dirs():
    """Ensure essential output and temporary directories exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
