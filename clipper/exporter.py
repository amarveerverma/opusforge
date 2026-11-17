import os
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np

from clipper.config import TEMP_DIR, OUTPUT_DIR, ensure_dirs
from clipper.transcriber import TranscriptResult, WordTiming
from clipper.scorer import ScoredClip


def format_ass_timestamp(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_word_synced_ass(
    words: List[WordTiming],
    clip_start: float,
    clip_end: float,
    output_ass_path: Path,
    words_per_group: int = 4
) -> Path:
    """
    Generate an ASS subtitle file with animated word-level highlights
    (Opus Clip style karaoke highlight effect).
    """
    # Filter words to clip range and adjust times relative to clip start (0.0)
    rel_words: List[WordTiming] = []
    for w in words:
        if w.start >= clip_start - 0.2 and w.end <= clip_end + 0.3:
            rel_start = max(0.0, round(w.start - clip_start, 2))
            rel_end = max(rel_start + 0.1, round(w.end - clip_start, 2))
            # Clean punctuation for uppercase display
            clean_w = w.word.strip().upper()
            if clean_w:
                rel_words.append(WordTiming(
                    word=clean_w,
                    start=rel_start,
                    end=rel_end,
                    probability=w.probability
                ))

    # Chunk words into small punchy groups of 3 to 5 words
    groups: List[List[WordTiming]] = []
    current_group: List[WordTiming] = []

    for w in rel_words:
        current_group.append(w)
        # End group if we hit target size or a natural punctuation stop
        if len(current_group) >= words_per_group or any(p in w.word for p in [".", "!", "?"]):
            groups.append(current_group)
            current_group = []

    if current_group:
        groups.append(current_group)

    # Build ASS script content
    # Color format in ASS is &HAABBGGRR (Hex)
    # Bright Yellow: &H0000E5FF or &H0000D7FF
    # Clean White: &H00FFFFFF
    # Deep Black Outline: &H00000000
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,66,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,6,3,2,60,60,420,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    for grp in groups:
        if not grp:
            continue
        grp_start = grp[0].start
        grp_end = grp[-1].end

        # For each word in the group, create an event where that word is highlighted
        for active_idx, target_word in enumerate(grp):
            w_start = target_word.start
            # If it's the last word in group, display until end of word or next group
            w_end = grp[active_idx + 1].start if active_idx + 1 < len(grp) else grp_end

            if w_end <= w_start:
                w_end = w_start + 0.2

            formatted_tokens = []
            for i, word_obj in enumerate(grp):
                if i == active_idx:
                    # Highlight active word: Gold/Yellow with slight pulse scale
                    token = f"{{\\c&H002BF5FF\\b1\\fscx112\\fscy112}}{word_obj.word}{{\\r\\b1}}"
                else:
                    token = word_obj.word
                formatted_tokens.append(token)

            line_text = " ".join(formatted_tokens)
            start_str = format_ass_timestamp(w_start)
            end_str = format_ass_timestamp(w_end)

            event_line = f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}"
            ass_lines.append(event_line)

    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    output_ass_path.write_text("\n".join(ass_lines), encoding="utf-8")
    return output_ass_path


def compute_face_center_reframe(
    video_path: str,
    clip_start: float,
    clip_end: float,
    orig_w: int,
    orig_h: int,
    target_w_crop: int
) -> int:
    """
    Detect the active speaker's horizontal center using OpenCV face detection
    across sample frames in the clip, and calculate the optimal crop offset X.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return max(0, (orig_w - target_w_crop) // 2)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    start_frame = int(clip_start * fps)
    end_frame = int(clip_end * fps)

    # Sample ~6 frames evenly spaced across the clip for fast robust median tracking
    sample_indices = np.linspace(start_frame, end_frame, num=6, dtype=int)
    face_centers_x: List[int] = []

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    for f_idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f_idx))
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(40, 40))

        if len(faces) > 0:
            # Pick largest detected face
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            fx, fy, fw, fh = largest_face
            center_x = fx + (fw // 2)
            face_centers_x.append(center_x)

    cap.release()

    if face_centers_x:
        # Use median for robustness against camera movements or false detections
        chosen_center = int(np.median(face_centers_x))
    else:
        # Fallback to horizontal center
        chosen_center = orig_w // 2

    # Calculate crop X offset such that chosen_center is centered in target_w_crop
    crop_x = chosen_center - (target_w_crop // 2)
    # Clamp within video bounds
    crop_x = max(0, min(crop_x, orig_w - target_w_crop))
    # Make sure crop_x is even (required for yuv420p)
    crop_x = (crop_x // 2) * 2

    return crop_x


def export_vertical_clip(
    source_video_path: str,
    clip: ScoredClip,
    words: List[WordTiming],
    output_dir: Path,
    target_width: int = 1080,
    target_height: int = 1920
) -> str:
    """
    Exports a vertical 9:16 video using ffmpeg:
    - Auto-reframes to keep active speaker centered
    - Burns in word-synced animated karaoke captions
    - Encodes to fast, high-quality H.264 mp4
    """
    ensure_dirs()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Probe source video dimensions
    cap = cv2.VideoCapture(str(source_video_path))
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
    cap.release()

    # Calculate 9:16 crop box from original height
    target_crop_w = int(round(orig_h * (9.0 / 16.0)))
    if target_crop_w % 2 != 0:
        target_crop_w -= 1

    if target_crop_w > orig_w:
        target_crop_w = orig_w
        target_crop_h = int(round(orig_w * (16.0 / 9.0)))
        if target_crop_h % 2 != 0:
            target_crop_h -= 1
        crop_x = 0
        crop_y = max(0, (orig_h - target_crop_h) // 2)
    else:
        target_crop_h = orig_h
        crop_x = compute_face_center_reframe(
            source_video_path,
            clip.start_time,
            clip.end_time,
            orig_w,
            orig_h,
            target_crop_w
        )
        crop_y = 0

    # Generate ASS subtitle file
    clean_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in clip.title).strip().replace(" ", "_")
    clip_filename = f"clip_{clip.id}_{clean_title[:30]}_score{clip.virality_score}.mp4"
    ass_path = TEMP_DIR / f"subtitles_{clip.id}.ass"
    generate_word_synced_ass(words, clip.start_time, clip.end_time, ass_path)

    # Windows ffmpeg subtitle path formatting:
    # Forward slashes, colon escaped as \:
    ass_path_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")

    out_clip_path = output_dir / clip_filename

    # Build ffmpeg filter chain:
    # 1. Crop to 9:16 region centered on speaker
    # 2. Scale to target_width x target_height (e.g. 1080x1920)
    # 3. Burn in ASS word-synced subtitles
    filter_chain = (
        f"crop={target_crop_w}:{target_crop_h}:{crop_x}:{crop_y},"
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
        f"subtitles='{ass_path_escaped}'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(clip.start_time),
        "-to", str(clip.end_time),
        "-i", str(source_video_path),
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_clip_path)
    ]

    print(f"[*] Exporting vertical 9:16 clip #{clip.id} ({clip.start_time}s - {clip.end_time}s)...")
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0:
        # If subtitles filter failed (e.g. libass missing or path escaping issue), fallback without subtitles
        print(f"[!] Subtitle overlay failed ({res.stderr[:200]}). Falling back to clean reframe export.")
        fallback_filter = (
            f"crop={target_crop_w}:{target_crop_h}:{crop_x}:{crop_y},"
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
        )
        cmd_fallback = [
            "ffmpeg", "-y",
            "-ss", str(clip.start_time),
            "-to", str(clip.end_time),
            "-i", str(source_video_path),
            "-vf", fallback_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_clip_path)
        ]
        subprocess.run(cmd_fallback, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    print(f"[+] Clip #{clip.id} successfully exported: {out_clip_path.name}")
    return str(out_clip_path.resolve())


def export_top_clips(
    source_video_path: str,
    scored_clips: List[ScoredClip],
    words: List[WordTiming],
    top_n: int = 3,
    output_dir: Optional[Path] = None
) -> List[ScoredClip]:
    """
    Export the top N ranked clips as vertical 9:16 mp4s with auto-reframe and burned-in captions.
    """
    target_dir = output_dir or OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    top_clips = scored_clips[:top_n]
    for clip in top_clips:
        exported_path = export_vertical_clip(
            source_video_path=source_video_path,
            clip=clip,
            words=words,
            output_dir=target_dir
        )
        clip.exported_file = exported_path

    return scored_clips
