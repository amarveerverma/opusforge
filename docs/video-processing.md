# ClipForge — Video Processing, Reframing & Rendering Pipeline

## 1. Overview
Transforming a 16:9 widescreen video into a 9:16 vertical short requires three distinct engineering systems:
1. **Intelligent Subject-Aware Reframing**: Dynamically cropping 1080x1920 from widescreen footage without jerky pans or cutting off the speaker's head.
2. **Dynamic Animated Captions**: Generating word-level synchronized karaoke subtitles using ASS (Advanced SubStation Alpha) formatting.
3. **Hardware NVENC Rendering**: Delivering 60fps/30fps MP4s at 1080x1920 in seconds via NVIDIA hardware encoding.

---

## 2. Smart Vertical Reframing (16:9 to 9:16)

### 2.1 The Framing Problem
A 16:9 1080p video has dimensions `1920 x 1080`.  
A 9:16 vertical video has dimensions `1080 x 1920`.  
To fit 16:9 into 9:16 without distortion or pillarboxing, we crop a vertical window of width `w = (1080 / 1920) * source_height = 607.5px` (for 1080p source), and scale it up to `1080 x 1920`.

The challenge is calculating the horizontal offset `X` smoothly over time:
- Centered crop: `X = (1920 - 607.5) / 2 = 656px`
- Dynamic tracking: `X(t) = face_center_x(t) - (crop_width / 2)`

### 2.2 Smoothing & Deadbands (EMA Filter)
Human eyes perceive sudden micro-pans as jarring camera shake. ClipForge implements an Exponential Moving Average (EMA) with a **deadband**:
- If the speaker moves by less than 5% of screen width, the camera does **not** move (deadband).
- When the speaker shifts significantly, the camera pans smoothly with smoothing factor `alpha = 0.08`:
  $$X_{\text{smooth}}(t) = \alpha \cdot X_{\text{target}}(t) + (1 - \alpha) \cdot X_{\text{smooth}}(t - 1)$$
- Clamping ensures the crop box never exceeds the video boundaries: `0 <= X <= source_width - crop_width`.

### 2.3 Headroom & Rule of Thirds
The crop maintains professional vertical composition: the speaker's eye line is positioned at approximately **30%–35%** down from the top edge of the 9:16 frame.

### 2.4 Fallback Framing Modes
1. **Single Speaker**: Active smooth pan-and-scan.
2. **Two Speakers**:
   - Dynamic switch (cuts framing to the person currently speaking according to diarization / face motion).
   - Or Split Screen (Top speaker / Bottom speaker).
3. **No Face Detected (Screen Share / B-roll / Gaming)**:
   - Centered crop.
   - Blurred background fill: Original 16:9 video scaled and heavily blurred behind the sharp 9:16 content.

---

## 3. Dynamic Animated Captions (ASS Subtitles)

ASS (Advanced SubStation Alpha) subtitles provide pixel-perfect control over fonts, colors, borders, shadows, and word-level karaoke animations without requiring video re-encoding for every style preview.

### 3.1 Styling Engine
- **Font**: Montserrat-Black / Impact / Poppins-Bold (clean, punchy, easily readable on mobile).
- **Font Size**: 48–56pt for 1080x1920.
- **Base Color**: Crisp White (`&H00FFFFFF`).
- **Highlight Color**: Neon Gold / Yellow (`&H0000D4FF`) or Vibrant Cyan / Violet.
- **Outline & Shadow**: 4px black outline (`&H00000000`) with 2px shadow to guarantee readability against any video background.
- **Positioning**: Safe zone at vertical alignment `\an2` (bottom-centered), offset 220px from the bottom to avoid TikTok / Instagram Reels like/comment icons.

### 3.2 Karaoke Word Highlighting (`\k` tags)
WhisperX provides exact `start` and `end` timestamps for each word. ClipForge transforms words into animated groups (3 to 6 words per screen) using ASS karaoke tags:
```
Dialogue: 0,0:00:01.20,0:00:03.40,Default,,0,0,0,,{\k35}This {\k45}is {\k50}the {\k60}future
```
As the speaker speaks, each word transitions from the base color to the highlight color in exact synchrony with speech.

---

## 4. Hardware NVENC Video Rendering

### 4.1 FFmpeg Pipeline Command Structure
```bash
ffmpeg -y -ss {start_time} -to {end_time} -i "{input_video}" \
  -filter_complex "[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1080:1920:flags=lanczos,ass='{ass_file}'[outv]" \
  -map "[outv]" -map 0:a \
  -c:v h264_nvenc -preset p5 -tune hq -cq 20 -b:v 6500k -maxrate 9000k -bufsize 12000k \
  -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart "{output_mp4}"
```

### 4.2 Quality Checks
Every render is validated by an automated post-flight verification script:
1. File exists and size > 500 KB.
2. Duration matches requested clip length (± 0.5s).
3. MP4 header integrity verified via `ffprobe`.
4. Audio track is present and synchronized.
