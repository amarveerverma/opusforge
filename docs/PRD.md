# ClipForge — Product Requirements Document (PRD)

## 1. Product Vision
**ClipForge** is a privacy-first, local-first AI video repurposing studio inspired by OpusClip. It enables content creators, podcasters, educators, and video editors to transform long-form landscape videos into viral, high-converting 9:16 vertical shorts (TikTok, YouTube Shorts, Instagram Reels) completely on their local PC, powered by their local NVIDIA GPU.

## 2. Core Value Propositions
1. **100% Local Processing & Complete Privacy**: Videos, audio, transcripts, and metadata never leave the user's computer.
2. **GPU-Accelerated Performance**: Leverages local NVIDIA Tensor cores for WhisperX speech recognition and NVENC for ultra-fast 1080x1920 video encoding.
3. **Smart Story & Narrative Discovery**: Identifies complete narrative moments (Hook, Flow, Value, Payoff) rather than chopping arbitrary sentence fragments.
4. **Automated Dynamic Captions**: Generates synchronized, animated karaoke captions in popular creator styles (MrBeast, Hormozi, Clean Modern).
5. **Intelligent Subject-Aware Framing**: Tracks faces and subjects dynamically to crop widescreen 16:9 into portrait 9:16 with smooth panning.
6. **No Subscriptions or Cloud Fees**: Unlimited local processing without recurring SaaS costs.

## 3. User Personas
- **Solo Content Creator / Podcaster**: Records 30–60 minute interviews or discussions and needs 5–10 high-impact shorts weekly.
- **Educator / Tutorial Maker**: Wants to extract concise, self-contained educational nuggets from long lectures.
- **Privacy-Conscious Professional**: Produces confidential corporate webinars, client interviews, or internal demos that cannot be uploaded to third-party cloud services.

## 4. Key Workflows (User Journey)
1. **Project Creation & Media Upload**:
   - User opens `localhost:3000`.
   - Clicks "New Project", inputs a title, and selects a local video file (`.mp4`, `.mov`, `.webm`, `.mkv`).
   - Supplies natural language guidance (e.g., *"Find 5 educational moments between 30 and 60 seconds with strong hooks"*).
2. **Automated AI Analysis Pipeline**:
   - Audio extraction & WhisperX word-level transcription.
   - PySceneDetect visual cut detection.
   - MediaPipe speaker face detection & trajectory smoothing.
   - Narrative arc fusion & Opus Virality Scoring (0–100).
3. **AI Suggestions & Discovery Gallery**:
   - User reviews ranked clip suggestions with virality score badges, category breakdowns, hooks, and explanation cards.
   - Can preview candidate clips in an in-browser vertical player.
4. **Interactive Studio Editing**:
   - Refine start and end timestamps with waveform/timeline scrubber.
   - Edit transcription text or fix misspellings.
   - Change caption styles (font, colors, uppercase, highlighting, positioning).
   - Adjust horizontal crop offset or select multi-speaker split view.
5. **Hardware Rendering & Export**:
   - User clicks "Render Clip".
   - FFmpeg NVENC renders the 1080x1920 MP4 with burned-in subtitles at 100+ FPS.
   - User previews the finished video and clicks "Download" or "Open Folder".

## 5. Non-Functional Requirements
- **Performance**: A 10-minute 1080p video should complete full transcription, analysis, and discovery in under 2 minutes on the RTX 4060 GPU.
- **Stability**: Zero CUDA out-of-memory errors through sequential execution and strict garbage collection.
- **Storage Integrity**: Source files are strictly read-only and never modified or deleted.
- **Cross-Browser UI**: Smooth web experience on modern desktop browsers (Chrome, Edge, Brave, Firefox).
