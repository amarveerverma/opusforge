# ClipForge — Frontend Architecture & UI Design Guide

## 1. Stack & Architecture
- **Framework**: Next.js 14/15 (App Router).
- **Language**: TypeScript (`strict: true`).
- **Styling**: Tailwind CSS + `shadcn/ui` component patterns.
- **Iconography**: Lucide React.
- **State & Data Fetching**: React Hooks + SWR / TanStack Query for caching and real-time SSE stream consumption.

---

## 2. Design System & Aesthetics
- **Theme**: Premium Dark Studio (inspired by OpusClip, Descript, and Linear).
- **Palette**:
  - Background: Deep obsidian `#09090B` / `#0C0C0E`
  - Cards & Panels: Dark slate `#18181B` with subtle borders (`border-white/10`)
  - Accent Color: Electric Violet `#8B5CF6` / `#7C3AED`
  - Highlighting & Virality Badges: Emerald `#10B981` (High score), Amber `#F59E0B` (Medium score), Crimson `#EF4444` (Low score)
  - Typography: Clean sans-serif (Inter / Geist Sans), high contrast white text `#F4F4F5` and muted gray `#A1A1AA`.

---

## 3. Screen Breakdown

### Screen 1: Dashboard (`/`)
- Top Bar: ClipForge branding, system status pill (GPU VRAM meter, RAM usage), "New Project" button.
- Storage Widget: Free SSD space meter and project count.
- Recent Projects Grid: Cards showing video thumbnail, title, duration, clips generated, status badge, and "Open Studio" button.

### Screen 2: New Project Modal / Page (`/projects/new`)
- Drag-and-drop video upload zone with real-time file size & format validation.
- Project title input.
- Natural language instructions textarea (e.g. *"Find the 5 most engaging educational moments, create 30–60 second clips, focus on speaker"*).
- Duration sliders: Min duration (15s–60s) and Max duration (30s–120s).
- Target clip count selector (3, 5, 10).
- "Start AI Analysis" button.

### Screen 3: Live Pipeline Progress (`/projects/[id]/processing`)
- Step-by-step pipeline visualization:
  - Ingestion & Metadata ➔ Audio Extraction ➔ WhisperX Transcription ➔ Diarization & Scenes ➔ Face Detection ➔ AI Clip Discovery ➔ Complete.
- Progress bar and active stage indicator.
- Elapsed time counter and live GPU telemetry.

### Screen 4: AI Results & Suggestions (`/projects/[id]`)
- Ranked candidate clips displayed as interactive cards:
  - 9:16 Video preview / animated hover thumbnail.
  - Virality Score Badge (e.g. `94/100 · Grade A+`).
  - Score Breakdown Dials (Hook, Flow, Value, Emotion).
  - Opening Hook preview text and excerpt transcript.
  - "Why this was chosen" explanation box.
  - Action buttons: "Edit Clip", "Instant Render".

### Screen 5: Clip Studio Editor (`/projects/[id]/clips/[clip_id]`)
- Center: Vertical 9:16 video player preview with interactive timeline scrubber.
- Timeline Bar: Draggable start and end trimming handles.
- Left Panel: Transcript editor with click-to-jump word sync.
- Right Panel:
  - Framing Selector: Auto-Face Tracking, Split Screen, or Manual Pan offset.
  - Caption Studio: Preset switchers (MrBeast, Hormozi, Clean, Cyberpunk), font size, color pickers, vertical position slider.
- Bottom Bar: "Save Changes" and "Render Final MP4" button with estimated render time.

### Screen 6: Export Library (`/projects/[id]/exports`)
- Gallery of rendered 1080x1920 MP4 clips.
- In-browser playback with audio controls.
- "Download MP4" button and "Reveal in File Explorer" button.
- Quality validation report: Resolution, bitrate, FPS, file size, encoder used.
