# ClipForge — Local AI Video Repurposing Studio

> **Transform long videos into viral 9:16 vertical shorts (TikTok, Reels, Shorts) completely offline on your PC with NVIDIA GPU hardware acceleration.**

Inspired by the workflow and virality intelligence of **OpusClip**, ClipForge is a 100% local, personal video repurposing studio. No cloud subscriptions, no video uploads leaving your machine, and zero API token costs.

---

## 🚀 Key Capabilities

1. **Local AI Multimodal Video Analysis**:
   - **WhisperX Transcription**: Word-level timestamps (`w.start`, `w.end`, `probability`) run locally in FP16 on NVIDIA RTX 4060 GPU with deterministic VRAM eviction.
   - **Speaker Diarization**: Offline acoustic speaker segmentation isolating who speaks when.
   - **Scene Cut Detection**: PySceneDetect `ContentDetector` identifying visual cut boundaries.
   - **MediaPipe Facial Tracking**: Samples keyframes at 4 FPS with Exponential Moving Average (EMA) smoothing and a 5% deadband window to eliminate camera jitter.

2. **7-Factor Opus Virality Index (0–100)**:
   - Evaluates each narrative moment on:
     - **Hook Strength (20%)**: First 3-second questions, high-intensity words, speech velocity.
     - **Narrative Flow (20%)**: Sentence-aligned boundaries, zero mid-word cuts.
     - **Standalone Context (15%)**: Eliminates dangling starts (*"and"*, *"so"*, *"but"*).
     - **Educational Value (15%)**: Frameworks, actionable insights, steps.
     - **Emotional Impact (15%)**: Stakes, exclamations, transformational vocabulary.
     - **Ending Quality (10%)**: Definite takeaway or punchline.
     - **Visual Potential (5%)**: Subject framing stability.
   - Returns letter grades (`A+`, `A`, `B+`, `B`, `C`), score breakdown dials, hook quotes, and why-chosen rationale.

3. **Smart Vertical Reframing (16:9 to 9:16)**:
   - Dynamic 9:16 cropping ($608 \times 1080$ scaled to $1080 \times 1920$ via Lanczos).
   - Rule-of-thirds headroom placing speaker eyes at 30–35% from the top of the frame.
   - **Multi-Mode Framing**:
     - `smart_track`: Active speaker trajectory follower.
     - `blur_background`: Clean blurred landscape backdrop for screen shares, coding tutorials, and B-roll.
     - `split_screen`: Dual-speaker interview layout ($1080 \times 960$ per speaker stacked vertically).
     - `center`: Static center crop fallback.
     - `manual`: Real-time horizontal focal slider ($0.0 \dots 1.0$).

4. **Dynamic Subtitles & Viral Presets**:
   - Word-by-word synchronized karaoke lighting using Advanced SubStation Alpha (`.ass`) formatting.
   - **MrBeast**: Bold Arial Black, neon yellow/gold highlight, heavy 6px black border, 3px shadow.
   - **Hormozi**: Heavy Impact font, neon red highlight, 6px outline, 3-word punchy bursts.
   - **Minimalist**: Clean sans-serif, soft cyan highlight, subtle 2px outline, natural casing.
   - Elevated safe margin ($240\text{px}$) to avoid mobile UI overlay obstruction.

5. **Hardware NVENC Video Rendering**:
   - Single-pass FFmpeg pipeline integrating trim, 9:16 crop, Lanczos scale, and ASS subtitle burn-in.
   - NVIDIA GPU accelerated (`h264_nvenc`) with automatic CPU `libx264` safety fallback.
   - Automated post-flight QA validation (duration, $1080 \times 1920$ dimensions, audio sync).
   - FastStart container (`-movflags +faststart`) enabling instant HTTP 206 browser scrubbing.

---

## 🖥️ Target Hardware

ClipForge is optimized specifically for:
- **OS**: Windows 11 64-bit
- **GPU**: NVIDIA GeForce RTX 4060 Laptop GPU (8 GB VRAM, Ada Lovelace)
- **CPU**: 13th Gen Intel Core i7-13620H (10 Cores, 16 Threads)
- **RAM**: 16 GB DDR5
- **FFmpeg**: Gyan.dev 8.1.2 with `h264_nvenc`, `av1_nvenc`, and `libass`
- **Python**: 3.11.15 in `.venv` with CUDA 12 & cuDNN 9 (`cublas64_12.dll`)

---

## ⚡ Quick Start (One Command)

### Option 1: Double-Click Batch Launcher (Windows)
Double-click `start_clipforge.bat` in the repository root.

### Option 2: Command Line
```powershell
# From the repository root (c:\clipper)
.venv\Scripts\python.exe scripts\run_clipforge.py
```

This launches both servers simultaneously:
- **Next.js Studio Frontend**: `http://localhost:3000`
- **FastAPI Backend API**: `http://localhost:8000`
- **Interactive OpenAPI Documentation**: `http://localhost:8000/docs`

---

## 👥 How to Run on Another PC (Setup from Scratch)

If you or anyone else wants to run ClipForge on another Windows, Mac, or Linux computer:

### 1. Prerequisites
- **Git**: [git-scm.com](https://git-scm.com/)
- **Python**: 3.10 or 3.11 ([python.org](https://www.python.org/))
- **Node.js**: 18.x or 20.x ([nodejs.org](https://nodejs.org/))
- **FFmpeg**: Must be installed and added to your system `PATH` ([ffmpeg.org](https://ffmpeg.org/download.html) or `winget install Gyan.FFmpeg` on Windows)

### 2. Clone the Repository
```bash
git clone https://github.com/amarveerverma/opusforge.git
cd opusforge
```

### 3. Setup Backend (Python Virtual Environment)
```bash
# Create virtual environment
python -m venv .venv

# Activate it:
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

*(Optional for NVIDIA GPU users)*: If you have an NVIDIA RTX GPU, ensure PyTorch with CUDA 12 is installed:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4. Setup Frontend (Next.js)
```bash
cd frontend
npm install
cd ..
```

### 5. Launch ClipForge
- **Windows**: Double-click `start_clipforge.bat` or run:
  ```powershell
  python scripts/run_clipforge.py
  ```
- **macOS / Linux**:
  ```bash
  python3 scripts/run_clipforge.py
  ```

Open your browser at **`http://localhost:3000`**!

---

## 📱 User Workflow

1. **Dashboard (`http://localhost:3000`)**:
   - View live GPU VRAM, RAM, and Disk metrics.
   - Drag and drop your video file (MP4, WebM, MOV, MKV) and provide optional instructions (e.g. *"Find 5 educational moments between 30 and 60 seconds"*).
2. **Project Discovery Hub (`/projects/[id]`)**:
   - Click **Run AI Discovery** to execute transcription, multi-modal analysis, and virality scoring.
   - Review ranked candidate cards with score badges, hook quotes, and selection rationale.
3. **Clip Studio Editor (`/projects/[id]/clips/[clip_id]`)**:
   - Adjust start/end trim boundaries with timeline scrubber.
   - Switch framing modes (`smart_track`, `blur_background`, `split_screen`, `manual`).
   - Switch subtitle presets (`MrBeast`, `Hormozi`, `Minimalist`) or customize font sizes.
   - Click **Render 9:16 Short** to encode using your NVIDIA GPU.
4. **Export Library (`/projects/[id]/exports`)**:
   - Watch rendered vertical shorts in-browser.
   - 1-click **Download MP4** or **Reveal in Windows Explorer**.

---

## 🏗️ Repository Architecture

```
c:\clipper\
├── backend/
│   └── app/
│       ├── config.py              # Environment configuration & directories
│       ├── database.py            # SQLite WAL connection manager & migrations
│       ├── main.py                # FastAPI entry point & CORS
│       ├── telemetry.py           # Live NVML GPU & hardware telemetry
│       ├── core/
│       │   ├── ingestion.py       # Chunked streaming, FFprobe metadata, thumbnails
│       │   ├── transcription.py   # Faster-Whisper GPU FP16 with word timestamps
│       │   ├── scene_detect.py    # PySceneDetect scene boundaries
│       │   ├── diarization.py     # Offline MFCC & PyAnnote speaker separation
│       │   ├── face_tracker.py    # MediaPipe face tracking & EMA trajectory
│       │   ├── clip_discovery.py  # 7-factor Opus virality scoring & candidate fusion
│       │   ├── reframer.py        # 9:16 crop calculation, deadband, blurred bg fallback
│       │   ├── subtitles.py       # Dynamic ASS subtitle generator & viral presets
│       │   └── renderer.py        # Single-pass FFmpeg NVENC renderer with QA audit
│       └── routers/
│           ├── system.py          # /health & /system/status telemetry
│           ├── projects.py        # Upload, stream (HTTP 206), thumbnails
│           ├── transcripts.py     # Speech transcription & SRT persistence
│           ├── analysis.py        # Diarization, scenes & face tracking
│           ├── clips.py           # AI discovery & framing updates
│           └── renders.py         # Hardware rendering, download & explorer reveal
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Dark studio dashboard & upload dropzone
│   │   │   └── projects/[id]/
│   │   │       ├── page.tsx       # AI discovery hub & candidate virality gallery
│   │   │       ├── exports/page.tsx # Rendered 9:16 shorts library
│   │   │       └── clips/[clip_id]/page.tsx # Clip studio editor
│   │   └── lib/
│   │       └── api.ts             # Typed REST client with progress callbacks
│   └── package.json
├── data/                          # 100% local database & project artifacts
│   ├── database/clipforge.db      # SQLite database in WAL mode
│   └── projects/{id}/
├── tests/                         # Comprehensive 41-test automated suite
├── scripts/
│   └── run_clipforge.py           # Dual-server local development orchestrator
└── start_clipforge.bat            # Double-clickable Windows launcher
```

---

## 🧪 Automated Test Suite

Run the full 41-test suite across all phases:

```powershell
$env:PYTHONPATH="."
.venv\Scripts\python.exe -m pytest tests/ -v
```

All 41 tests across ingestion, WhisperX transcription, diarization, MediaPipe face tracking, 7-factor virality discovery, 9:16 reframing, ASS dynamic subtitles, NVENC video rendering, Next.js routes, and edge-case benchmarks pass with 100% success.
