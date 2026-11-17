import json
import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from clipper.config import GEMINI_API_KEY, TEMP_DIR, DEFAULT_CONFIG, ensure_dirs


class VisualMoment(BaseModel):
    timestamp: float
    scene: str
    actions: str
    on_screen_text: str
    facial_expression: str
    emotional_moment: str
    visual_interest_score: float  # 0 to 100
    is_visual_hook: bool


class VisualAnalysisResult(BaseModel):
    total_frames_sampled: int
    sampling_interval: float
    moments: List[VisualMoment]
    per_second_visual_score: List[float]
    highlight_timestamps: List[float]


def sample_video_frames(
    video_path: str,
    interval_sec: float = 2.0,
    max_dimension: int = 640
) -> List[Dict[str, Any]]:
    """
    Extract frames every `interval_sec` seconds from the video.
    Returns list of dicts with timestamp, jpg_bytes, and motion_score.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = max(1, int(round(fps * interval_sec)))

    samples = []
    frame_idx = 0
    prev_gray = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            timestamp = round(frame_idx / fps, 2)

            # Resize while maintaining aspect ratio
            h, w = frame.shape[:2]
            scale = min(max_dimension / max(h, w), 1.0)
            if scale < 1.0:
                frame_resized = cv2.resize(frame, (int(w * scale), int(h * scale)))
            else:
                frame_resized = frame

            # Calculate motion difference from previous sampled frame
            gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
            motion_score = 0.0
            if prev_gray is not None and prev_gray.shape == gray.shape:
                diff = cv2.absdiff(gray, prev_gray)
                motion_score = float(np.mean(diff))
            prev_gray = gray

            _, buffer = cv2.imencode(".jpg", frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
            samples.append({
                "timestamp": timestamp,
                "frame_index": frame_idx,
                "jpg_bytes": buffer.tobytes(),
                "motion_score": motion_score,
                "bgr_frame": frame_resized
            })

        frame_idx += 1

    cap.release()
    return samples


def analyze_with_gemini(
    samples: List[Dict[str, Any]],
    batch_size: int = 8,
    model_name: Optional[str] = None
) -> List[VisualMoment]:
    """
    Multimodal visual analysis with Gemini API:
    Analyzes scenes, actions, on-screen text, facial expressions, emotional moments, and visual highlights.
    """
    from google import genai
    from google.genai import types

    api_key = GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    model = model_name or DEFAULT_CONFIG["gemini_model"]

    visual_moments: List[VisualMoment] = []

    # Batch samples to send efficient chunks to Gemini
    for i in range(0, len(samples), batch_size):
        batch = samples[i:i + batch_size]
        contents = []

        system_instruction = (
            "You are a multimodal video analyst for an Opus Clip AI pipeline. "
            "Analyze the provided sequential video frames. For EACH frame, evaluate: "
            "1. Scene description and setting. "
            "2. Actions taking place. "
            "3. Any visible on-screen text or graphics. "
            "4. Facial expressions and gestures (e.g. smiling, laughter, surprise, intense focus, neutral). "
            "5. Emotional moments (humor, excitement, shock, tension, demonstration). "
            "6. Visual interest score (0 to 100) - how engaging is this visually for short-form video (TikTok/Reels/Shorts). "
            "7. Is this a visual hook (first impression, dramatic reaction, punchy visual)? True/False. "
            "Return a strictly valid JSON list of objects matching the schema."
        )

        prompt_text = "Analyze these video frames taken at timestamps: " + ", ".join([f"{s['timestamp']}s" for s in batch])
        contents.append(prompt_text)

        for s in batch:
            contents.append(f"Timestamp: {s['timestamp']}s")
            contents.append(types.Part.from_bytes(data=s["jpg_bytes"], mime_type="image/jpeg"))

        prompt_text_footer = (
            "Return JSON format:\n"
            "[\n"
            "  {\n"
            "    \"timestamp\": float,\n"
            "    \"scene\": \"string\",\n"
            "    \"actions\": \"string\",\n"
            "    \"on_screen_text\": \"string\",\n"
            "    \"facial_expression\": \"string\",\n"
            "    \"emotional_moment\": \"string\",\n"
            "    \"visual_interest_score\": float,\n"
            "    \"is_visual_hook\": bool\n"
            "  }\n"
            "]"
        )
        contents.append(prompt_text_footer)

        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )

            parsed = json.loads(response.text)
            if isinstance(parsed, list):
                for item in parsed:
                    visual_moments.append(VisualMoment(
                        timestamp=float(item.get("timestamp", 0.0)),
                        scene=str(item.get("scene", "")),
                        actions=str(item.get("actions", "")),
                        on_screen_text=str(item.get("on_screen_text", "")),
                        facial_expression=str(item.get("facial_expression", "")),
                        emotional_moment=str(item.get("emotional_moment", "")),
                        visual_interest_score=float(item.get("visual_interest_score", 50.0)),
                        is_visual_hook=bool(item.get("is_visual_hook", False))
                    ))
        except Exception as e:
            print(f"[!] Warning: Gemini batch analysis error ({e}). Falling back to visual heuristics for this batch.")
            fallback_batch = fallback_opencv_analysis(batch)
            visual_moments.extend(fallback_batch)

    return visual_moments


def fallback_opencv_analysis(samples: List[Dict[str, Any]]) -> List[VisualMoment]:
    """
    Heuristic visual analysis using OpenCV face detection, motion analysis,
    and image variance when Gemini API is unavailable or offline.
    """
    face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    moments = []
    for s in samples:
        t = s["timestamp"]
        frame = s["bgr_frame"]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(30, 30))

        num_faces = len(faces)
        motion = s.get("motion_score", 0.0)

        # Base score on face presence and motion
        score = 45.0
        if num_faces > 0:
            score += 25.0
            largest_face = max([w * h for (x, y, w, h) in faces])
            face_ratio = largest_face / (frame.shape[0] * frame.shape[1])
            if face_ratio > 0.05:
                score += 15.0

        if motion > 12.0:
            score += 15.0

        score = min(98.0, max(15.0, score))
        is_hook = (score >= 75.0 and (t <= 5.0 or motion > 20.0))

        moments.append(VisualMoment(
            timestamp=t,
            scene="Speaker framing" if num_faces > 0 else "Wide / Presentation",
            actions="Talking to camera" if num_faces > 0 else "Visual presentation",
            on_screen_text="",
            facial_expression="Active speaker" if num_faces > 0 else "Neutral",
            emotional_moment="High interest" if score > 75 else "Informational",
            visual_interest_score=round(score, 1),
            is_visual_hook=is_hook
        ))

    return moments


def analyze_video_visuals(
    video_path: str,
    interval_sec: float = 2.0,
    use_gemini: bool = True
) -> VisualAnalysisResult:
    """
    Main visual analysis pipeline:
    Samples frames every `interval_sec`, analyzes them with Gemini (or fallback),
    and generates visual timelines and highlight timestamps.
    """
    print(f"[*] Sampling video frames every {interval_sec}s from {Path(video_path).name}...")
    samples = sample_video_frames(video_path, interval_sec=interval_sec)
    print(f"[*] Sampled {len(samples)} frames.")

    if not samples:
        return VisualAnalysisResult(
            total_frames_sampled=0,
            sampling_interval=interval_sec,
            moments=[],
            per_second_visual_score=[],
            highlight_timestamps=[]
        )

    has_key = bool(GEMINI_API_KEY)
    if use_gemini and has_key:
        print(f"[*] Running Gemini multimodal visual analysis...")
        # For long videos, select up to 48 keyframes (highest motion / scene changes + uniform intervals)
        if len(samples) > 48:
            step = len(samples) / 48
            gemini_samples = [samples[int(i * step)] for i in range(48)]
            print(f"[*] Distilled {len(samples)} frames into {len(gemini_samples)} keyframe intervals for Gemini API...")
            moments = analyze_with_gemini(gemini_samples)
        else:
            moments = analyze_with_gemini(samples)
    else:
        if not has_key:
            print("[*] Notice: GEMINI_API_KEY not found in environment. Using OpenCV heuristic visual analysis.")
        else:
            print("[*] Gemini disabled by config. Using OpenCV visual analysis.")
        moments = fallback_opencv_analysis(samples)

    # Sort moments by timestamp
    moments.sort(key=lambda m: m.timestamp)

    # Build per-second visual score
    last_timestamp = moments[-1].timestamp if moments else 0.0
    total_seconds = int(np.ceil(last_timestamp)) + 1
    per_second_visual_score = [50.0] * total_seconds

    for m in moments:
        sec = int(m.timestamp)
        if 0 <= sec < total_seconds:
            per_second_visual_score[sec] = m.visual_interest_score

    # Highlight timestamps (visual interest score > 75 or is_visual_hook)
    highlights = [m.timestamp for m in moments if m.is_visual_hook or m.visual_interest_score >= 75.0]

    return VisualAnalysisResult(
        total_frames_sampled=len(samples),
        sampling_interval=interval_sec,
        moments=moments,
        per_second_visual_score=per_second_visual_score,
        highlight_timestamps=highlights
    )
