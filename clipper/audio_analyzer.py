import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from pydantic import BaseModel

from clipper.config import TEMP_DIR, ensure_dirs


class AudioMoment(BaseModel):
    timestamp: float
    moment_type: str  # "peak", "reaction", "silence_start", "rapid_speech", "pause"
    score: float
    description: str


class AudioAnalysisResult(BaseModel):
    audio_path: str
    duration: float
    avg_energy: float
    peak_count: int
    energy_peaks: List[float]
    silence_intervals: List[Tuple[float, float]]
    reaction_moments: List[AudioMoment]
    # 1-second resolution energy profile (0-100)
    per_second_energy: List[float]
    per_second_speech_rate: List[float]


def extract_audio_track(video_path: str, output_wav_path: Optional[str] = None) -> str:
    """Extract 16kHz mono WAV audio from video file using ffmpeg."""
    ensure_dirs()
    if output_wav_path is None:
        video_p = Path(video_path)
        output_wav_path = str(TEMP_DIR / f"{video_p.stem}_audio.wav")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_wav_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_wav_path


def analyze_audio(video_or_audio_path: str) -> AudioAnalysisResult:
    """
    Programmatic audio analysis using librosa and numpy:
    - Volume/energy peaks (RMS)
    - Silence gaps
    - Laughter / applause / excitement reactions (spectral centroid & energy)
    - Speech-rate changes (onset density over sliding windows)
    """
    import librosa

    path_obj = Path(video_or_audio_path)
    if path_obj.suffix.lower() in [".mp4", ".mov", ".mkv", ".avi", ".webm"]:
        wav_path = extract_audio_track(video_or_audio_path)
    else:
        wav_path = str(video_or_audio_path)

    # Load audio at 16kHz
    sr = 16000
    y, _ = librosa.load(wav_path, sr=sr, mono=True)
    duration = float(len(y) / sr)

    if duration <= 0:
        return AudioAnalysisResult(
            audio_path=wav_path,
            duration=0.0,
            avg_energy=0.0,
            peak_count=0,
            energy_peaks=[],
            silence_intervals=[],
            reaction_moments=[],
            per_second_energy=[],
            per_second_speech_rate=[]
        )

    # 1. Energy / RMS analysis
    hop_length = 512
    frame_length = 2048
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    times = librosa.times_like(rms, sr=sr, hop_length=hop_length)

    # Normalize RMS to 0 - 100
    rms_max = np.max(rms) if np.max(rms) > 0 else 1.0
    rms_normalized = (rms / rms_max) * 100.0

    # Aggregate RMS per second (0 to duration)
    total_seconds = int(np.ceil(duration))
    per_second_energy = [0.0] * total_seconds
    for i, t in enumerate(times):
        sec = int(t)
        if 0 <= sec < total_seconds:
            per_second_energy[sec] = max(per_second_energy[sec], float(rms_normalized[i]))

    # Detect energy peaks (e.g. above mean + 1.2 * std)
    mean_energy = float(np.mean(rms_normalized))
    std_energy = float(np.std(rms_normalized))
    peak_threshold = mean_energy + 1.1 * std_energy

    energy_peaks: List[float] = []
    # Simple local maximum filter
    for i in range(1, len(rms_normalized) - 1):
        if rms_normalized[i] > peak_threshold:
            if rms_normalized[i] > rms_normalized[i - 1] and rms_normalized[i] > rms_normalized[i + 1]:
                t = round(float(times[i]), 2)
                # Keep peaks at least 1.5 seconds apart
                if not energy_peaks or (t - energy_peaks[-1]) >= 1.5:
                    energy_peaks.append(t)

    # 2. Silence detection using frame-level RMS
    silence_intervals: List[Tuple[float, float]] = []
    silence_thresh = max(4.0, mean_energy * 0.20)
    in_silence = False
    silence_start = 0.0

    for i in range(len(rms_normalized)):
        t = float(times[i])
        is_quiet = rms_normalized[i] < silence_thresh
        if is_quiet and not in_silence:
            in_silence = True
            silence_start = t
        elif not is_quiet and in_silence:
            in_silence = False
            silence_dur = t - silence_start
            if silence_dur >= 0.5:  # meaningful pause
                silence_intervals.append((round(silence_start, 2), round(t, 2)))

    if in_silence:
        silence_dur = duration - silence_start
        if silence_dur >= 0.5:
            silence_intervals.append((round(silence_start, 2), round(duration, 2)))

    # 3. Speech rate / Onset density
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
    onset_times = librosa.frames_to_time(onsets, sr=sr, hop_length=hop_length)

    per_second_speech_rate = [0.0] * total_seconds
    for ot in onset_times:
        sec = int(ot)
        if 0 <= sec < total_seconds:
            per_second_speech_rate[sec] += 1.0

    # 4. Reaction moments: Laughter / Applause / Excitement detection
    # Spectral centroid measures audio brightness
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    sc_mean = float(np.mean(spectral_centroid))
    sc_std = float(np.std(spectral_centroid))
    sc_thresh = sc_mean + 1.2 * sc_std

    reaction_moments: List[AudioMoment] = []
    for i in range(len(spectral_centroid)):
        t = round(float(times[i]), 2)
        if spectral_centroid[i] > sc_thresh and rms_normalized[i] > (mean_energy + 0.8 * std_energy):
            # Check if we already registered a reaction close to this timestamp
            if not reaction_moments or (t - reaction_moments[-1].timestamp) >= 3.0:
                moment_type = "laughter_or_applause" if spectral_centroid[i] > (sc_mean + 1.8 * sc_std) else "vocal_excitement"
                reaction_moments.append(AudioMoment(
                    timestamp=t,
                    moment_type=moment_type,
                    score=round(float(rms_normalized[i]), 1),
                    description=f"{moment_type.replace('_', ' ').title()} peak detected at {t}s"
                ))

    return AudioAnalysisResult(
        audio_path=wav_path,
        duration=round(duration, 2),
        avg_energy=round(mean_energy, 2),
        peak_count=len(energy_peaks),
        energy_peaks=energy_peaks,
        silence_intervals=silence_intervals,
        reaction_moments=reaction_moments,
        per_second_energy=[round(v, 2) for v in per_second_energy],
        per_second_speech_rate=[round(v, 2) for v in per_second_speech_rate]
    )
