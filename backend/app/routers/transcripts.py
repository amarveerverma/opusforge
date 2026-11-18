import json
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from ..database import get_db
from ..config import settings
from ..core.transcription import (
    extract_audio_for_transcription,
    transcribe_audio,
    save_transcript_artifacts,
    TranscriptResult,
)

router = APIRouter(prefix="/projects/{project_id}/transcript", tags=["Transcripts"])

class TranscribeRequest(BaseModel):
    model_size: Optional[str] = "base"
    compute_type: Optional[str] = "float16"
    language: Optional[str] = None

class TranscriptUpdateRequest(BaseModel):
    full_text: Optional[str] = None
    segments: Optional[list] = None

@router.post("", response_model=TranscriptResult)
async def trigger_transcription(project_id: str, payload: Optional[TranscribeRequest] = None):
    """
    Extracts 16kHz audio from the source video and executes GPU-accelerated
    transcription with precision word timestamps.
    """
    if payload is None:
        payload = TranscribeRequest()
        
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        proj = await cursor.fetchone()
        
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    source_path_str = proj["source_file_path"]
    if not source_path_str or not Path(source_path_str).exists():
        raise HTTPException(status_code=400, detail="Project has no uploaded video file yet")
        
    source_path = Path(source_path_str)
    proj_dir = settings.PROJECTS_DIR / project_id
    audio_path = proj_dir / "transcripts" / "audio.wav"
    
    # 1. Extract 16kHz mono audio via FFmpeg
    try:
        extract_audio_for_transcription(source_path, audio_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {e}")
        
    # 2. Run speech recognition on GPU with VRAM protection
    try:
        result = transcribe_audio(
            audio_path=audio_path,
            model_size=payload.model_size or settings.WHISPER_MODEL,
            device=settings.WHISPER_DEVICE,
            compute_type=payload.compute_type or settings.WHISPER_COMPUTE_TYPE,
            language=payload.language,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
        
    # 3. Persist transcript artifacts
    save_transcript_artifacts(proj_dir, result)
    
    # 4. Update project status in SQLite
    async with get_db() as db:
        await db.execute(
            "UPDATE projects SET status = 'transcribed' WHERE id = ?",
            (project_id,)
        )
        await db.commit()
        
    return result

@router.get("", response_model=Dict[str, Any])
async def get_transcript(project_id: str):
    """
    Returns the current working transcript JSON with word-level timestamps.
    """
    proj_dir = settings.PROJECTS_DIR / project_id
    transcript_path = proj_dir / "transcripts" / "transcript.json"
    
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript has not been generated for this project yet")
        
    try:
        data = json.loads(transcript_path.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read transcript: {e}")

@router.patch("", response_model=Dict[str, Any])
async def update_transcript(project_id: str, payload: TranscriptUpdateRequest):
    """
    Allows user corrections to transcript text or segments while preserving
    the original raw immutable transcript.
    """
    proj_dir = settings.PROJECTS_DIR / project_id
    transcript_path = proj_dir / "transcripts" / "transcript.json"
    
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found")
        
    try:
        data = json.loads(transcript_path.read_text(encoding="utf-8"))
        if payload.full_text is not None:
            data["full_text"] = payload.full_text
        if payload.segments is not None:
            data["segments"] = payload.segments
            
        transcript_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        
        # Also update plaintext
        if payload.full_text:
            (proj_dir / "transcripts" / "transcript.txt").write_text(payload.full_text, encoding="utf-8")
            
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update transcript: {e}")
