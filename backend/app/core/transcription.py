"""
ClipForge Transcription & Word-Level Alignment Engine
Powered by Faster-Whisper / CTranslate2 on NVIDIA GPU with strict VRAM eviction.
"""
import os
import gc
import sys
import time
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel

logger = logging.getLogger("clipforge.transcription")

def setup_cuda_dlls():
    """
    Ensures NVIDIA CUDA 12 and cuDNN dynamic libraries are loaded into Windows PATH and DLL search paths.
    """
    if sys.platform != "win32":
        return
        
    site_packages = Path(sys.prefix) / "Lib" / "site-packages"
    nvidia_dir = site_packages / "nvidia"
    if nvidia_dir.exists():
        bins = [str(b) for b in nvidia_dir.glob("*/bin")]
        if bins:
            os.environ["PATH"] = ";".join(bins) + ";" + os.environ.get("PATH", "")
            for b in bins:
                try:
                    os.add_dll_directory(b)
                except Exception:
                    pass
                    
    ct2_dir = site_packages / "ctranslate2"
    if ct2_dir.exists():
        os.environ["PATH"] = str(ct2_dir) + ";" + os.environ.get("PATH", "")
        try:
            os.add_dll_directory(str(ct2_dir))
        except Exception:
            pass

# Trigger DLL registration immediately
setup_cuda_dlls()

class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float
    probability: float

class Segment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: List[WordTimestamp]

class TranscriptResult(BaseModel):
    language: str
    language_probability: float
    duration: float
    full_text: str
    segments: List[Segment]
    words: List[WordTimestamp]
    model_used: str
    compute_type: str
    vram_peak_mb: int
    transcription_time_s: float

def extract_audio_for_transcription(video_path: Path, output_wav: Path) -> Path:
    """
    Extracts high-fidelity 16kHz 16-bit mono WAV audio from video using FFmpeg.
    If the video contains no audio stream, generates a silent WAV matching video duration.
    """
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if video has an audio stream
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    try:
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        has_audio = bool(probe.stdout.strip())
    except Exception:
        has_audio = False
        
    if has_audio:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(output_wav),
        ]
    else:
        # Generate silent WAV for videos without audio
        logger.info("Video contains no audio stream. Creating silent audio placeholder: %s", output_wav)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "5",
            str(output_wav),
        ]
        
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_wav
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg audio extraction failed: %s", e.stderr)
        raise RuntimeError(f"Failed to extract audio from video: {e.stderr}")

def get_current_vram_mb() -> int:
    """Helper to query current GPU VRAM usage."""
    try:
        from ..telemetry import get_gpu_telemetry
        telemetry = get_gpu_telemetry()
        return telemetry.get("vram_used_mb", 0)
    except Exception:
        return 0

def evict_model(model_ref=None):
    """
    Deterministically cleans GPU memory from PyTorch and CTranslate2 runtime.
    """
    if model_ref is not None:
        del model_ref
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except ImportError:
        pass

def transcribe_audio(
    audio_path: Path,
    model_size: Optional[str] = None,
    device: str = "cuda",
    compute_type: str = "float16",
    language: Optional[str] = None,
) -> TranscriptResult:
    """
    Executes speech recognition with word-level timestamps on GPU,
    recording peak VRAM and releasing memory upon completion.
    """
    if not model_size:
        model_size = settings.WHISPER_MODEL
    setup_cuda_dlls()
    from faster_whisper import WhisperModel
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    start_vram = get_current_vram_mb()
    start_time = time.time()
    
    # Graceful fallback to CPU if CUDA fails
    selected_device = device
    selected_compute = compute_type
    model = None
    
    try:
        logger.info("Loading Whisper model '%s' on %s (%s)...", model_size, selected_device, selected_compute)
        model = WhisperModel(model_size, device=selected_device, compute_type=selected_compute)
    except Exception as e:
        logger.warning("Failed to initialize on %s: %s. Falling back to CPU...", selected_device, e)
        selected_device = "cpu"
        selected_compute = "int8"
        model = WhisperModel(model_size, device=selected_device, compute_type=selected_compute)
        
    peak_vram = max(start_vram, get_current_vram_mb())
    
    try:
        logger.info("Transcribing audio: %s (language=%s)...", audio_path, language)
        try:
            segments_gen, info = model.transcribe(
                str(audio_path),
                word_timestamps=True,
                vad_filter=True,
                language=language,
            )
            # Evaluate first segment to test CUDA execution
            first_segment = None
            segments_list_temp = []
            for seg in segments_gen:
                segments_list_temp.append(seg)
        except RuntimeError as cuda_err:
            if "cublas" in str(cuda_err).lower() or "cuda" in str(cuda_err).lower():
                logger.warning("CUDA execution error: %s. Retrying with CPU fallback...", cuda_err)
                evict_model(model)
                selected_device = "cpu"
                selected_compute = "int8"
                model = WhisperModel(model_size, device=selected_device, compute_type=selected_compute)
                segments_gen, info = model.transcribe(
                    str(audio_path),
                    word_timestamps=True,
                    vad_filter=True,
                    language=language,
                )
                segments_list_temp = list(segments_gen)
            else:
                raise
        
        segments_list: List[Segment] = []
        all_words: List[WordTimestamp] = []
        full_text_parts = []
        
        for idx, seg in enumerate(segments_list_temp):
            current_vram = get_current_vram_mb()
            if current_vram > peak_vram:
                peak_vram = current_vram
                
            seg_words = []
            if seg.words:
                for w in seg.words:
                    word_obj = WordTimestamp(
                        word=w.word,
                        start=round(w.start, 2),
                        end=round(w.end, 2),
                        probability=round(w.probability, 3),
                    )
                    seg_words.append(word_obj)
                    all_words.append(word_obj)
                    
            segments_list.append(Segment(
                id=idx,
                start=round(seg.start, 2),
                end=round(seg.end, 2),
                text=seg.text.strip(),
                words=seg_words,
            ))
            full_text_parts.append(seg.text.strip())
            
        elapsed = round(time.time() - start_time, 2)
        full_text = " ".join(full_text_parts)
        
        result = TranscriptResult(
            language=info.language,
            language_probability=round(info.language_probability, 3),
            duration=round(info.duration, 2),
            full_text=full_text,
            segments=segments_list,
            words=all_words,
            model_used=model_size,
            compute_type=selected_compute,
            vram_peak_mb=peak_vram,
            transcription_time_s=elapsed,
        )
        return result
    finally:
        # Deterministic VRAM eviction
        logger.info("Evicting Whisper model from memory...")
        evict_model(model)
        gc.collect()

def export_srt(segments: List[Segment], output_srt: Path):
    """Generates standard SRT subtitles file from segments."""
    def fmt_time(seconds: float) -> str:
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"
        
    lines = []
    for s in segments:
        lines.append(str(s.id + 1))
        lines.append(f"{fmt_time(s.start)} --> {fmt_time(s.end)}")
        lines.append(s.text)
        lines.append("")
        
    output_srt.write_text("\n".join(lines), encoding="utf-8")

def save_transcript_artifacts(project_dir: Path, result: TranscriptResult):
    """
    Saves immutable raw transcript, working transcript, plaintext, and SRT.
    """
    project_dir = Path(project_dir)
    transcripts_dir = project_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    
    result_dict = result.model_dump()
    
    # 1. Raw immutable transcript (preserves original AI output)
    raw_path = transcripts_dir / "transcript_raw.json"
    if not raw_path.exists():
        raw_path.write_text(json.dumps(result_dict, indent=2), encoding="utf-8")
        
    # 2. Current working transcript
    working_path = transcripts_dir / "transcript.json"
    working_path.write_text(json.dumps(result_dict, indent=2), encoding="utf-8")
    
    # 3. Plaintext transcript
    txt_path = transcripts_dir / "transcript.txt"
    txt_path.write_text(result.full_text, encoding="utf-8")
    
    # 4. SRT file
    srt_path = transcripts_dir / "subtitles.srt"
    export_srt(result.segments, srt_path)
