# Opus Clip AI — Multimodal Video Clipping Pipeline

A local, multimodal AI video clipping pipeline inspired by **Opus Clip** (`opus.pro`). It takes long videos (YouTube URLs or local files), analyzes them using transcript, visual scenes, and audio energy curves, detects self-contained narrative moments, computes the **Opus Virality Score** (0–99 with Hook, Flow, Value, and Trend factor breakdowns), reframes speakers to vertical 9:16 using OpenCV face detection, and exports high-quality vertical videos with burned-in word-synced animated karaoke captions.

---

## 🌟 Key Features

1. **Dual Input Support**:
   - Direct YouTube URL downloading via `yt-dlp`.
   - Local video files (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`).
2. **Multimodal Analysis ("ClipAnything" approach)**:
   - **Speech & Timestamps**: Word-level timestamps using `faster-whisper` (runs fast on CPU or GPU with `int8`).
   - **Visuals & Expressions**: Samples frames every ~2s and analyzes them with Gemini Multimodal API (`google-genai`) for scenes, actions, on-screen text, facial expressions, and emotional moments (with automatic local OpenCV fallback).
   - **Audio Dynamics**: Programmatic audio analysis with `librosa` for volume peaks, silence pauses, speech rate, and laughter/applause/excitement reactions.
3. **Signal Fusion**:
   - Fuses transcript sentence boundaries, visual interest, and audio energy.
   - Detects self-contained narrative arcs (15–90 seconds) with clean start/end sentence boundaries.
4. **Opus Virality Scoring (0–99)**:
   - **HOOK**: First 3 seconds attention grab + curiosity gap.
   - **FLOW**: Logical progression, narrative pacing, and payoff.
   - **VALUE**: Educational utility + emotional resonance + relatable insight.
   - **TREND**: Alignment with current short-form video pacing (TikTok/Reels/Shorts).
   - Letter grades (`A` / `B` / `C`) and one-line justifications for each factor.
5. **Vertical 9:16 Auto-Reframe & Captions**:
   - Auto-reframes landscape video to 9:16 (`1080x1920`) keeping the active speaker centered using OpenCV face detection with smoothing.
   - Burns in word-synced animated karaoke subtitles (ASS subtitles) with active word color highlighting.
6. **Dual Dashboard**:
   - **CLI Dashboard**: Beautiful terminal table rendered with `rich`.
   - **Local Web UI**: Modern dark-mode web application (FastAPI + Tailwind CSS) with in-browser vertical video preview, score dials, and instant export.

---

## 📁 Project Architecture

```
c:\clipper\
├── clipper/
│   ├── __init__.py
│   ├── config.py              # Environment variables, defaults, paths
│   ├── downloader.py          # YouTube (yt-dlp) and local video loader & ffprobe
│   ├── transcriber.py         # Faster-whisper with word-level timestamps
│   ├── visual_analyzer.py     # Frame sampling (~2s) + Gemini multimodal visual analysis
│   ├── audio_analyzer.py      # Librosa audio energy peaks, silence gaps, reactions
│   ├── fusion_detector.py     # Multimodal signal fusion -> 15-90s self-contained candidates
│   ├── scorer.py              # Opus Virality Score (0-99), letter grades (A/B/C) & justifications
│   ├── exporter.py            # 9:16 vertical crop with face tracking & word-synced ASS captions
│   ├── dashboard.py           # Rich CLI table & JSON analysis report generation
│   ├── pipeline.py            # Orchestrator running stages 1 through 7
│   └── web_app.py             # FastAPI backend for local web dashboard
├── web/
│   └── index.html             # Responsive dark-mode Opus Clip web interface
├── tests/
│   ├── test_audio_analyzer.py # Audio energy & silence tests
│   ├── test_fusion.py         # Signal fusion tests
│   ├── test_scorer.py         # Scoring and ranking tests
│   └── test_exporter.py       # ASS word karaoke subtitle generation tests
├── output/                    # Exported 9:16 clips and analysis_report.json
├── temp/                      # Intermediate audio WAVs, sampled frames, ASS files
├── .env.example               # Template environment configuration
├── requirements.txt           # Python dependencies
├── run_clipper.py             # Main CLI execution entry point
└── run_dashboard.py           # Standalone web dashboard launcher
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **Python**: Version 3.10+ (tested on Python 3.11 Windows 64-bit).
- **FFmpeg**: Ensure `ffmpeg` and `ffprobe` are installed and in your system `PATH`.
  ```powershell
  ffmpeg -version
  ```

### 2. Clone or Enter Project Directory
```powershell
cd c:\clipper
```

### 3. Initialize Python Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Configure API Key
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Edit `.env` and add your Google Gemini API key:
```env
GEMINI_API_KEY=AIzaSy...
```
*(Note: If no API key is provided, the pipeline automatically runs in local offline heuristic mode using OpenCV and programmatic heuristics!)*

---

## 🎬 How to Run

### Option A: Process a Local Video File
```powershell
python run_clipper.py --file "C:\path\to\video.mp4" --top-n 3
```

### Option B: Process a YouTube Video URL
```powershell
python run_clipper.py --url "https://www.youtube.com/watch?v=EXAMPLE_ID" --top-n 3
```

### Option C: Process and Automatically Launch Web Dashboard
```powershell
python run_clipper.py --file "temp\sample_podcast.mp4" --top-n 3 --web
```
Open your browser at `http://localhost:8000` to preview the 9:16 vertical clips, view virality scores, and download exported videos.

### Option D: Launch Web Dashboard Directly
```powershell
python run_dashboard.py --port 8000
```

---

## ⚙️ CLI Options

| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--url` | String | None | YouTube URL to download and analyze |
| `--file` | String | None | Local video file path (`.mp4`, `.mov`, `.mkv`) |
| `--top-n` | Integer | `3` | Number of top-ranked clips to export as 9:16 MP4 |
| `--min-duration` | Float | `15.0` | Minimum duration in seconds for clips |
| `--max-duration` | Float | `90.0` | Maximum duration in seconds for clips |
| `--output-dir` | String | `output` | Directory for exported clips and JSON report |
| `--no-gemini` | Flag | `False` | Force offline heuristic mode without API calls |
| `--web` | Flag | `False` | Automatically launch web dashboard after processing |
| `--port` | Integer | `8000` | Port for the web dashboard |

---

## 📊 Output Artifacts

After running, the following files are produced in the `output/` folder:
1. **Vertical 9:16 MP4 Clips**:
   - `clip_1_<title>_score<score>.mp4`
   - Cropped and centered on the active speaker with face detection.
   - High-contrast, word-by-word karaoke captions burned into the video.
2. **Analysis Report (`analysis_report.json`)**:
   - Full transcript with word timestamps.
   - Visual moment descriptions and highlights.
   - Audio energy peaks, silence gaps, and reaction points.
   - Candidate clips with Hook, Flow, Value, and Trend scores, letter grades, and one-line justifications.

---

## 🧪 Running Tests

Run the test suite across all modules:
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python tests\test_audio_analyzer.py
.\.venv\Scripts\python tests\test_fusion.py
.\.venv\Scripts\python tests\test_scorer.py
.\.venv\Scripts\python tests\test_exporter.py
```
All unit tests should display `PASSED`.
