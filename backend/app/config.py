"""
ClipForge Configuration Module
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

# Base workspace directory (c:\clipper)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    APP_NAME: str = "ClipForge"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server network
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]
    
    # Storage Paths
    ROOT_DIR: Path = ROOT_DIR
    DATA_DIR: Path = ROOT_DIR / "data"
    DB_PATH: Path = ROOT_DIR / "data" / "database" / "clipforge.db"
    PROJECTS_DIR: Path = ROOT_DIR / "data" / "projects"
    CACHE_DIR: Path = ROOT_DIR / "data" / "cache"
    LOGS_DIR: Path = ROOT_DIR / "data" / "logs"
    
    # Hardware & Model Defaults
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cuda"
    WHISPER_COMPUTE_TYPE: str = "float16"
    
    # External AI Flags (strictly optional)
    ENABLE_EXTERNAL_AI: bool = False
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    HF_TOKEN: str = ""

settings = Settings()

# Ensure directories exist upon startup
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
settings.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
