"""
ClipForge Visual Scene Cut Detection Engine
Powered by PySceneDetect (ContentDetector).
Identifies abrupt and gradual visual scene transitions.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel
import scenedetect
from scenedetect import detect, ContentDetector, AdaptiveDetector

logger = logging.getLogger("clipforge.scene_detect")

class SceneCut(BaseModel):
    scene_id: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    start_frame: int
    end_frame: int

class SceneAnalysisResult(BaseModel):
    total_scenes: int
    scenes: List[SceneCut]
    cut_timestamps: List[float]

def detect_scenes(
    video_path: Path,
    threshold: float = 27.0,
    min_scene_len_sec: float = 1.0
) -> SceneAnalysisResult:
    """
    Analyzes visual frame differences across time to find scene boundaries.
    Runs on CPU using OpenCV difference matrices, consuming negligible VRAM.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    logger.info("Running scene detection on %s (threshold=%.1f)...", video_path, threshold)
    
    try:
        scene_list = detect(
            str(video_path),
            ContentDetector(threshold=threshold, min_scene_len=int(min_scene_len_sec * 30))
        )
    except Exception as e:
        logger.warning("Standard ContentDetector encountered issue: %s. Using fallback...", e)
        # Fallback to AdaptiveDetector
        try:
            scene_list = detect(str(video_path), AdaptiveDetector())
        except Exception as e2:
            logger.error("Scene detection failed: %s", e2)
            # Safe single-scene fallback
            return SceneAnalysisResult(
                total_scenes=1,
                scenes=[SceneCut(scene_id=0, start_seconds=0.0, end_seconds=0.0, duration_seconds=0.0, start_frame=0, end_frame=0)],
                cut_timestamps=[]
            )
            
    cuts: List[SceneCut] = []
    cut_timestamps: List[float] = []
    
    for idx, (start_time, end_time) in enumerate(scene_list):
        start_sec = round(start_time.seconds if hasattr(start_time, "seconds") else start_time.get_seconds(), 2)
        end_sec = round(end_time.seconds if hasattr(end_time, "seconds") else end_time.get_seconds(), 2)
        dur = round(end_sec - start_sec, 2)
        start_frame = start_time.frame_num if hasattr(start_time, "frame_num") else start_time.get_frames()
        end_frame = end_time.frame_num if hasattr(end_time, "frame_num") else end_time.get_frames()
        
        cuts.append(SceneCut(
            scene_id=idx,
            start_seconds=start_sec,
            end_seconds=end_sec,
            duration_seconds=dur,
            start_frame=start_frame,
            end_frame=end_frame,
        ))
        if start_sec > 0.05:
            cut_timestamps.append(start_sec)
            
    # If no cuts were detected, the entire video is a single continuous scene
    if not cuts:
        cuts.append(SceneCut(
            scene_id=0,
            start_seconds=0.0,
            end_seconds=0.0,
            duration_seconds=0.0,
            start_frame=0,
            end_frame=0,
        ))
        
    logger.info("Scene detection completed: found %d visual scenes.", len(cuts))
    return SceneAnalysisResult(
        total_scenes=len(cuts),
        scenes=cuts,
        cut_timestamps=sorted(list(set(cut_timestamps)))
    )
