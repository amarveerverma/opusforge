# ClipForge — Testing & Quality Assurance Plan

## 1. Overview
ClipForge enforces end-to-end testing across unit components, integration workflows, hardware boundaries, and rendering quality.

---

## 2. Test Suites

### Suite 1: Hardware & System Telemetry Tests (`tests/test_hardware.py`)
- Test GPU detection via NVML / pynvml.
- Verify accurate reporting of VRAM usage, system RAM, and free disk space.
- Verify memory eviction helper cleans PyTorch cache without throwing exceptions.

### Suite 2: Ingestion & Validation Tests (`tests/test_ingestion.py`)
- Verify FFprobe parses valid MP4, WebM, and MOV containers.
- Verify rejection of invalid or corrupted files.
- Verify thumbnail frame generation at specified timestamps.

### Suite 3: Speech & Alignment Tests (`tests/test_transcription.py`)
- Test WhisperX / faster-whisper on a short 10-second reference WAV file.
- Verify word-level timestamps are strictly increasing and non-negative.
- Verify VRAM is freed immediately after transcription completes.

### Suite 4: Diarization & Visual Tracking Tests (`tests/test_analysis.py`)
- Test PySceneDetect cut detection on a multi-scene test clip.
- Test MediaPipe face tracking: verify bounding boxes `(x, y, w, h)` are normalized `[0.0, 1.0]`.
- Verify EMA smoothing logic eliminates abrupt jumps.

### Suite 5: AI Discovery & Scoring Tests (`tests/test_scoring.py`)
- Test sentence boundary snapping: verify clips never start or end mid-sentence.
- Verify Opus Virality Score calculation adheres to weights (Hook 20%, Flow 20%, Value 15%, Emotion 15%, Context 15%, Ending 10%, Visual 5%).
- Verify non-overlapping candidate filtering.

### Suite 6: Subtitles & Rendering Tests (`tests/test_rendering.py`)
- Verify ASS subtitle file generation with valid `\k` karaoke duration tags.
- Execute a test render of a 5-second clip using `h264_nvenc` at 1080x1920.
- Execute fallback test with `libx264`.
- Run post-flight verification on rendered MP4: check file size, video streams, audio streams, and duration.

---

## 3. Benchmarking Protocol (OpusClip Comparison)
- Standard benchmark dataset:
  1. 1-person podcast interview (Lex Fridman style, 10 min).
  2. 2-person rapid conversation / debate (5 min).
  3. Screen share presentation / tutorial (5 min).
- Evaluation metrics:
  - Time-to-discovery (seconds from upload to candidate suggestions).
  - VRAM peak usage (must remain below 7.0 GB at all times).
  - Virality score relevance (human review of clip punchlines).
  - Video rendering speed (FPS and elapsed seconds for 60s render).
