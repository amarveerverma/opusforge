import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_db
from ..config import settings
from ..core.scene_detect import detect_scenes, SceneAnalysisResult
from ..core.face_tracker import track_faces_in_video, FaceTrackingResult
from ..core.diarization import diarize_audio, DiarizationResult

router = APIRouter(prefix="/projects/{project_id}/analysis", tags=["Analysis"])
logger = logging.getLogger("clipforge.analysis")

class AnalysisSummaryResponse(BaseModel):
    project_id: str
    scenes: SceneAnalysisResult
    diarization: DiarizationResult
    faces: FaceTrackingResult
    status: str

@router.post("", response_model=AnalysisSummaryResponse)
async def run_analysis(project_id: str):
    """
    Executes Phase 4 multi-modal analysis sequentially:
    1. Visual scene cut detection (PySceneDetect)
    2. Speaker audio diarization (pyannote or offline clustering)
    3. Facial tracking & trajectory analysis (MediaPipe)
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        proj = await cursor.fetchone()
        
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    source_path_str = proj["source_file_path"]
    if not source_path_str or not Path(source_path_str).exists():
        raise HTTPException(status_code=400, detail="Project video file not found")
        
    video_path = Path(source_path_str)
    proj_dir = settings.PROJECTS_DIR / project_id
    analysis_dir = proj_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    audio_path = proj_dir / "transcripts" / "audio.wav"
    
    # Ensure audio exists for diarization
    if not audio_path.exists():
        from ..core.transcription import extract_audio_for_transcription
        extract_audio_for_transcription(video_path, audio_path)
        
    # 1. Visual Scene Detection (CPU)
    logger.info("Executing scene cut detection for %s...", project_id)
    scenes_res = detect_scenes(video_path)
    (analysis_dir / "scenes.json").write_text(json.dumps(scenes_res.model_dump(), indent=2), encoding="utf-8")
    
    # 2. Speaker Diarization (Sequential)
    logger.info("Executing speaker diarization for %s...", project_id)
    diar_res = diarize_audio(audio_path, hf_token=settings.HF_TOKEN)
    (analysis_dir / "diarization.json").write_text(json.dumps(diar_res.model_dump(), indent=2), encoding="utf-8")
    
    # 3. Face Tracking (Sampled Keyframes)
    logger.info("Executing face tracking for %s...", project_id)
    faces_res = track_faces_in_video(video_path, sample_fps=4.0)
    (analysis_dir / "face_tracks.json").write_text(json.dumps(faces_res.model_dump(), indent=2), encoding="utf-8")
    
    # Update SQLite
    async with get_db() as db:
        await db.execute("UPDATE projects SET status = 'analyzed' WHERE id = ?", (project_id,))
        await db.commit()
        
    return AnalysisSummaryResponse(
        project_id=project_id,
        scenes=scenes_res,
        diarization=diar_res,
        faces=faces_res,
        status="analyzed",
    )

@router.get("", response_model=Dict[str, Any])
async def get_analysis_data(project_id: str):
    """
    Returns stored multi-modal analysis data for the project.
    """
    proj_dir = settings.PROJECTS_DIR / project_id
    analysis_dir = proj_dir / "analysis"
    
    scenes_file = analysis_dir / "scenes.json"
    diar_file = analysis_dir / "diarization.json"
    faces_file = analysis_dir / "face_tracks.json"
    
    if not scenes_file.exists() and not diar_file.exists():
        raise HTTPException(status_code=404, detail="Analysis data not generated yet")
        
    data = {}
    if scenes_file.exists():
        data["scenes"] = json.loads(scenes_file.read_text(encoding="utf-8"))
    if diar_file.exists():
        data["diarization"] = json.loads(diar_file.read_text(encoding="utf-8"))
    if faces_file.exists():
        data["faces"] = json.loads(faces_file.read_text(encoding="utf-8"))
        
    return data
