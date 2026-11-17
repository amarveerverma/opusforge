import numpy as np
import soundfile as sf
from pathlib import Path
from clipper.audio_analyzer import analyze_audio
from clipper.config import TEMP_DIR, ensure_dirs


def test_audio_analysis_on_synthetic_wav():
    ensure_dirs()
    wav_path = TEMP_DIR / "test_tone.wav"

    # Generate 5 seconds of audio with varying amplitude and a silence gap
    sr = 16000
    t = np.linspace(0, 5, sr * 5, endpoint=False)
    # 0-2s tone, 2-3.5s silence, 3.5-5s high energy tone
    signal = np.sin(2 * np.pi * 440 * t)
    signal[:sr * 2] *= 0.5
    signal[sr * 2:int(sr * 3.5)] *= 0.001
    signal[int(sr * 3.5):] *= 0.95

    sf.write(str(wav_path), signal, sr)

    result = analyze_audio(str(wav_path))
    assert result.duration >= 4.9
    assert len(result.per_second_energy) == 5
    assert len(result.silence_intervals) >= 1
    assert result.per_second_energy[4] > result.per_second_energy[2]
    print("test_audio_analysis_on_synthetic_wav: PASSED")


if __name__ == "__main__":
    test_audio_analysis_on_synthetic_wav()
