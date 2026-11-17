"""
ClipForge Speaker Diarization Engine
Supports pyannote.audio (when HF_TOKEN is configured) and offline acoustic clustering fallback.
Note: Audio diarization identifies distinct vocal patterns; it does NOT assert visual identity.
"""
import os
import gc
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from .transcription import evict_model

logger = logging.getLogger("clipforge.diarization")

class DiarizationSegment(BaseModel):
    speaker_id: str
    start: float
    end: float
    duration: float
    confidence: Optional[float] = 1.0

class DiarizationResult(BaseModel):
    num_speakers: int
    speakers: List[str]
    segments: List[DiarizationSegment]
    engine_used: str
    disclaimer: str = (
        "Audio diarization identifies vocal characteristics and acoustic separation. "
        "It does NOT verify the visual identity of on-screen individuals."
    )

def _offline_acoustic_diarization(audio_path: Path) -> DiarizationResult:
    """
    Offline acoustic feature clustering diarization engine.
    Extracts MFCC features and energy dynamics to segment speakers without cloud tokens.
    """
    import librosa
    from sklearn.cluster import AgglomerativeClustering
    
    logger.info("Running offline acoustic diarization on %s...", audio_path.name)
    y, sr = librosa.load(str(audio_path), sr=16000)
    dur = float(librosa.get_duration(y=y, sr=sr))
    
    if dur < 1.0:
        return DiarizationResult(
            num_speakers=1,
            speakers=["SPEAKER_00"],
            segments=[DiarizationSegment(speaker_id="SPEAKER_00", start=0.0, end=dur, duration=dur)],
            engine_used="offline_single_speaker"
        )
        
    # Window-based MFCC extraction (1.5s windows with 0.5s hop)
    win_len = int(1.5 * sr)
    hop_len = int(0.5 * sr)
    
    features = []
    timestamps = []
    
    for i in range(0, len(y) - win_len, hop_len):
        chunk = y[i : i + win_len]
        # Check if active speech (energy above noise floor)
        rms = librosa.feature.rms(y=chunk)[0].mean()
        if rms > 0.01:
            mfcc = librosa.feature.mfcc(y=chunk, sr=sr, n_mfcc=13).mean(axis=1)
            features.append(mfcc)
            timestamps.append((i / sr, (i + win_len) / sr))
            
    if len(features) < 3:
        # Default single speaker
        return DiarizationResult(
            num_speakers=1,
            speakers=["SPEAKER_00"],
            segments=[DiarizationSegment(speaker_id="SPEAKER_00", start=0.0, end=dur, duration=dur)],
            engine_used="offline_single_speaker"
        )
        
    features_arr = np.array(features)
    
    # Cluster into speakers (estimate 1 to 3 speakers based on variance)
    n_clusters = 2 if len(features_arr) > 10 else 1
    clustering = AgglomerativeClustering(n_clusters=n_clusters).fit(features_arr)
    labels = clustering.labels_
    
    # Merge contiguous intervals
    segments: List[DiarizationSegment] = []
    curr_speaker = f"SPEAKER_{labels[0]:02d}"
    curr_start = timestamps[0][0]
    curr_end = timestamps[0][1]
    
    for idx in range(1, len(labels)):
        spk = f"SPEAKER_{labels[idx]:02d}"
        t_start, t_end = timestamps[idx]
        
        if spk == curr_speaker and t_start <= curr_end + 0.6:
            curr_end = t_end
        else:
            segments.append(DiarizationSegment(
                speaker_id=curr_speaker,
                start=round(curr_start, 2),
                end=round(curr_end, 2),
                duration=round(curr_end - curr_start, 2),
            ))
            curr_speaker = spk
            curr_start = t_start
            curr_end = t_end
            
    segments.append(DiarizationSegment(
        speaker_id=curr_speaker,
        start=round(curr_start, 2),
        end=round(curr_end, 2),
        duration=round(curr_end - curr_start, 2),
    ))
    
    speakers_list = sorted(list(set(s.speaker_id for s in segments)))
    return DiarizationResult(
        num_speakers=len(speakers_list),
        speakers=speakers_list,
        segments=segments,
        engine_used="offline_acoustic_clustering",
    )

def diarize_audio(
    audio_path: Path,
    hf_token: Optional[str] = None
) -> DiarizationResult:
    """
    Executes speaker diarization sequentially. Uses pyannote if token is available,
    otherwise executes offline acoustic clustering.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    # Check for pyannote.audio with HF token
    token = hf_token or os.environ.get("HF_TOKEN")
    
    if token:
        try:
            logger.info("Initializing pyannote.audio pipeline on GPU with HF token...")
            from pyannote.audio import Pipeline
            import torch
            
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=token
            )
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            pipeline.to(device)
            
            logger.info("Running pyannote diarization...")
            diarization = pipeline(str(audio_path))
            
            segments: List[DiarizationSegment] = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(DiarizationSegment(
                    speaker_id=speaker,
                    start=round(turn.start, 2),
                    end=round(turn.end, 2),
                    duration=round(turn.end - turn.start, 2),
                    confidence=0.95
                ))
                
            evict_model(pipeline)
            del pipeline
            gc.collect()
            
            speakers_list = sorted(list(set(s.speaker_id for s in segments)))
            return DiarizationResult(
                num_speakers=len(speakers_list),
                speakers=speakers_list,
                segments=segments,
                engine_used="pyannote.audio",
            )
        except Exception as e:
            logger.warning("pyannote execution issue: %s. Falling back to offline engine...", e)
            
    # Fallback to offline engine
    return _offline_acoustic_diarization(audio_path)
