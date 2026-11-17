# ClipForge — Implementation Roadmap & Execution Plan

**Project**: ClipForge — Local AI Video Clipping Studio  
**Target Hardware**: Windows 11 · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM) · 16 GB RAM · 1 TB SSD  
**Architecture**: Next.js 14/15 Frontend (`localhost:3000`) + FastAPI Backend (`localhost:8000`) + SQLite + Local GPU Pipeline  

---

## Roadmap Overview

```
Phase 0: Machine & Environment Audit (COMPLETED)
   │
   ▼
Phase 1: Project Foundation (FastAPI + Next.js + SQLite + Storage Architecture)
   │
   ▼
Phase 2: Video Ingestion & Inspection (FFprobe + Thumbnails + Project Storage)
   │
   ▼
Phase 3: Transcription & Word-Level Alignment (WhisperX / Faster-Whisper + VRAM Safeguards)
   │
   ▼
Phase 4: Diarization & Visual Scene Analysis (PySceneDetect + MediaPipe + pyannote)
   │
   ▼
Phase 5: AI Clip Discovery & Explainable Scoring (Hook/Flow/Value + Natural Language Prompts)
   │
   ▼
Phase 6: Smart Vertical Reframing (9:16 Subject-Aware Tracking + Fallbacks)
   │
   ▼
Phase 7: Dynamic Captions & Hardware Rendering (ASS Subtitles + NVENC Acceleration)
   │
   ▼
Phase 8: Studio Web Interface Integration (Dashboard + Editor + Caption Studio + Export Library)
   │
   ▼
Phase 9: Quality Assurance, Benchmarking & Polish (Stress Tests + OpusClip Benchmark Suite)
```

---

## Detailed Phase Breakdown

### Phase 0: Machine & Environment Audit [COMPLETED]
- **Deliverables**:
  - Full hardware capability inspection (GPU, VRAM, CPU, RAM, Disk).
  - Verification of media engines (FFmpeg 8.1.2, NVENC `h264_nvenc`/`av1_nvenc`, `libass`).
  - Python 3.11 environment and CUDA driver capability verification.
  - Runtime architecture recommendation (Windows Native vs WSL2).
  - `docs/machine-audit.md` generated.
- **Exit Criteria**: All prerequisites verified; approval requested to start Phase 1.

---

### Phase 1: Project Foundation
- **Objectives**: Build the foundational scaffold for backend, frontend, database, and local filesystem hierarchy.
- **Backend**:
  - FastAPI application initialized on port 8000 with CORS and lifespan handlers.
  - SQLite database initialized via SQLAlchemy / aiosqlite with clean migrations/schema:
    - `projects` table (id, name, original_filename, file_path, duration, width, height, fps, status, created_at).
    - `jobs` table (id, project_id, stage, progress, status, error, started_at, completed_at).
    - `clips` table (id, project_id, start_time, end_time, title, hook, summary, score, score_breakdown, transcript, crop_config, caption_config, status).
    - `renders` table (id, clip_id, file_path, resolution, fps, duration, file_size, quality_report, created_at).
  - Health check (`/health`) and System status (`/system/status`) reporting real-time CPU, RAM, and GPU VRAM availability.
  - Project CRUD endpoints (`POST /projects`, `GET /projects`, `GET /projects/{id}`, `DELETE /projects/{id}`).
  - Structured local filesystem layout under `c:\clipper\data\`:
    - `data/database/`
    - `data/projects/{project_id}/source/`
    - `data/projects/{project_id}/thumbnails/`
    - `data/projects/{project_id}/transcripts/`
    - `data/projects/{project_id}/analysis/`
    - `data/projects/{project_id}/candidates/`
    - `data/projects/{project_id}/renders/`
- **Frontend**:
  - Modern Next.js application (App Router, TypeScript, Tailwind CSS, Lucide Icons).
  - API client connecting to `http://localhost:8000`.
  - Professional dark theme layout (OpusClip/CapFlow aesthetic: near-black `#0A0A0C`, slate surfaces `#16161A`, violet accents `#8B5CF6`).
  - Navigation header, project card grid, and system health status widget.
- **Exit Criteria**: Frontend loads at `localhost:3000`, communicates with FastAPI at `localhost:8000`, creates a project in SQLite, and displays live hardware metrics.

---

### Phase 2: Video Ingestion & Inspection
- **Objectives**: Enable robust file uploads and extraction of comprehensive media metadata.
- **Implementation**:
  - File upload endpoint with streaming chunked transfer to avoid memory spikes.
  - Input file validation: Check container types (`.mp4`, `.mov`, `.webm`, `.mkv`), file headers, corruption checks.
  - FFprobe metadata extractor:
    - Duration, video stream codecs, resolution, aspect ratio, frame rate, audio sample rate, channels.
  - Thumbnail generator: High-quality frame extraction at 10%, 25%, and 50% timestamps using FFmpeg.
  - API endpoints for serving thumbnails and raw source video chunks for browser preview.
- **Exit Criteria**: User can upload a video, see immediate metadata and thumbnails on the frontend, and view the original file playback.

---

### Phase 3: Transcription & Word-Level Alignment
- **Objectives**: Integrate WhisperX / faster-whisper with word-level timestamps and strict 8 GB VRAM management.
- **Implementation**:
  - Audio extraction pipeline: FFmpeg extraction to 16kHz mono WAV.
  - WhisperX engine wrapper:
    - Default profile: `large-v3-turbo` in FP16 (or `large-v3` configurable).
    - Batch size: 1 (safe for 8 GB VRAM).
    - Word-level timestamp alignment using Wav2Vec2.
  - VRAM eviction protocol: Explicitly evict models from GPU memory after transcription completes.
  - Transcript persistence: Store structured JSON (words, start, end, confidence) and text in project folder and database.
  - Transcript edit API: Allow correcting misheard words or punctuation.
- **Exit Criteria**: A 5-minute video transcribes accurately with word-level timestamps, and GPU VRAM returns to baseline (<500 MB) post-execution.

---

### Phase 4: Diarization & Visual Scene Analysis
- **Objectives**: Detect speaker changes, scene cuts, and locate faces across time.
- **Implementation**:
  - **PySceneDetect**: Detect sharp and gradual scene cuts using ContentDetector on CPU. Save scene cut timestamps.
  - **pyannote.audio Diarization**:
    - Load pyannote model sequentially (after Whisper is evicted).
    - Extract speaker intervals (`SPEAKER_00`, `SPEAKER_01`, etc.).
    - Graceful fallback: If Hugging Face token is absent, mark as single-speaker or voice-activity-detected.
  - **MediaPipe / OpenCV Face Tracking**:
    - Sample frames (e.g. 3–5 FPS or keyframes) to locate faces and bounding boxes.
    - Calculate face center `(x, y)` and bounding box size `(w, h)` per frame.
  - Multi-modal timestamp alignment: Align transcript sentences with speaker intervals and visual scenes.
- **Exit Criteria**: Analysis output JSON contains aligned scenes, speaker labels, and face trajectory data.

---

### Phase 5: AI Clip Discovery & Explainable Scoring
- **Objectives**: Discover coherent, standalone viral moments based on story arc and user instructions.
- **Implementation**:
  - **Natural Language Instruction Parser**: Parse user desires (e.g., "Find 5 educational moments between 30 and 60 seconds").
  - **Narrative Arc Boundary Engine**:
    - Ensure clips start and end on complete sentences and clause boundaries.
    - Prevent mid-sentence cutoffs or dangling thoughts.
    - Target window enforcement (30–60s default, or user-specified).
  - **Opus Virality Scoring System (0–100)**:
    - **Hook Strength (20%)**: Speed of narrative punchline in the first 3 seconds, question/curiosity gap.
    - **Narrative Flow (20%)**: Pacing, absence of dead silence, sentence density.
    - **Educational / Entertainment Value (15%)**: Key takeaway, insight density.
    - **Emotional Impact (15%)**: Audio dynamics, excitement peaks, expressive language.
    - **Standalone Context (15%)**: Does the clip make complete sense without external context?
    - **Ending Quality (10%)**: Strong closing statement, call to action, or punchline.
    - **Visual Potential (5%)**: Consistent presence of visible speakers or scene variety.
  - **Explainability**: Every candidate clip receives an overall score, letter grade (A/B/C), category breakdown, and a natural language "Why this was selected" explanation.
  - **Dual Engine Architecture**:
    - Offline algorithmic engine (Default): Uses sentiment, lexical markers, audio energy, and sentence structure.
    - Optional LLM engine: Queries Gemini / OpenAI for advanced comedic/storytelling nuance if configured.
- **Exit Criteria**: System produces a ranked list of top candidate clips with timestamps, titles, hooks, and detailed score cards.

---

### Phase 6: Smart Vertical Reframing (9:16)
- **Objectives**: Automatically reframe 16:9 widescreen video into professional 1080x1920 vertical format.
- **Implementation**:
  - Bounding Box Tracking & Smoothing:
    - Smooth crop coordinates across frames using exponential moving average (EMA) or Kalman filter to eliminate jerky camera jumps.
    - Apply rule-of-thirds headroom: place speaker's eyes at ~30–35% from the top of the 9:16 frame.
  - Multi-Person & No-Person Strategies:
    - Single active speaker: Dynamic pan-and-scan centering on the speaker.
    - Two speakers: Smart split screen (top/bottom) or switch-on-speech framing.
    - No face detected (e.g. gameplay, slides, screen share): Centered crop with blurred background padding or smart fit.
  - User Override: Allow the user in the UI to select custom crop offset (Left, Center, Right, or manual X position).
- **Exit Criteria**: Video renders with buttery-smooth camera tracking that keeps the speaker centered without unnatural motion.

---

### Phase 7: Dynamic Captions & Hardware Rendering
- **Objectives**: Generate word-synced animated karaoke subtitles and render high-resolution 1080x1920 MP4s via NVENC.
- **Implementation**:
  - **ASS (Advanced SubStation Alpha) Subtitle Engine**:
    - Generate precision word-level karaoke tags (`\k` / `\kf`).
    - Custom styles: Bold font (Montserrat / Impact / Poppins), uppercase, high-contrast outline, drop shadow.
    - Word highlighting: Active spoken word lights up in vibrant Yellow (`&H0000FFFF`) or Neon Violet (`&H00E040FB`).
    - Positioned within safe margins (bottom 25%, above TikTok/Reels UI overlay zones).
  - **Hardware NVENC Render Pipeline**:
    - FFmpeg command combining:
      - Video cropping / scaling filter (`crop=w:h:x:y,scale=1080:1920`)
      - Subtitle overlay filter (`ass='subtitles.ass'`)
      - Video encoder: `h264_nvenc` with `-preset p5 -cq 21 -b:v 6000k`
      - Audio encoder: `aac -b:a 192k`
    - Software fallback: Automatic retry with `libx264` if NVENC encounters any transient driver issue.
  - **Post-Render Quality Validation**:
    - Check file size > 0, duration matches expected clip bounds (±0.5s).
    - Verify audio stream exists and is synchronized.
    - Validate FFprobe container readability.
- **Exit Criteria**: Flawless 1080x1920 MP4 rendered with burned-in animated captions in seconds using NVENC hardware acceleration.

---

### Phase 8: Full Studio Web Interface Integration
- **Objectives**: Connect all backend capabilities to an intuitive, responsive Next.js web application.
- **Screens**:
  1. **Dashboard**: Projects overview, disk storage meter, GPU status monitor, quick resume.
  2. **New Project**: Drag-and-drop video upload, natural language prompt input ("Find 5 funny moments"), duration constraints, language selector.
  3. **Processing View**: Real-time SSE / WebSocket event stream showing step-by-step pipeline execution, elapsed time, and GPU usage.
  4. **AI Results Gallery**: Ranked clip cards with video preview, virality score badges, transcript excerpts, hooks, and "Why chosen" rationale.
  5. **Clip Editor**: Vertical 9:16 video player with scrubber, draggable start/end handles, transcript editor, and framing selector.
  6. **Caption Studio**: Font selector, color picker, preset switcher (MrBeast style, Hormozi style, Minimalist, Cyberpunk), position adjuster.
  7. **Export Library**: Rendered clips gallery, instant download, open local folder button, render quality reports.
- **Exit Criteria**: Complete end-to-end user journey executed from the browser without opening the terminal.

---

### Phase 9: Quality Assurance, Benchmarking & Polish
- **Objectives**: Stress test the full platform against real-world video archetypes and optimize performance.
- **Testing Scenarios**:
  - 1-person podcast / talking head (e.g. Lex Fridman style).
  - 2-person interview / discussion.
  - Screen share / lecture / presentation with no faces.
  - High-tempo gaming / action footage.
  - Extended long video (30–60 minutes) to verify stability and memory ceiling.
- **Side-by-Side Comparison**:
  - Benchmark against OpusClip / QuickReel standard outputs (virality score relevance, caption sync accuracy, render speed).
- **Exit Criteria**: Zero memory leaks, 100% test pass rate, verified render output quality.
