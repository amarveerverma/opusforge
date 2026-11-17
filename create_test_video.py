import os
import subprocess
from pathlib import Path
import cv2
import numpy as np

from clipper.config import TEMP_DIR, ensure_dirs


def create_sample_speech_wav(wav_path: Path) -> Path:
    """Generate multi-sentence spoken audio using Windows Speech Synthesis."""
    script = """
    Add-Type -AssemblyName System.Speech;
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;
    $synth.Rate = 0;
    $synth.SetOutputToWaveFile('""" + str(wav_path).replace("\\", "/") + """');
    $synth.Speak('Stop scrolling right now. Why does nobody talk about this unbelievable AI video secret? In 2026, content creators who rely on basic transcripts are completely falling behind.');
    Start-Sleep -Milliseconds 500;
    $synth.Speak('The real viral clips are discovered by fusing multimodal vision, audio energy peaks, and word level timestamps. When you analyze facial expressions and voice volume together, audience engagement skyrockets.');
    Start-Sleep -Milliseconds 600;
    $synth.Speak('Opus style reframing keeps the active speaker smoothly centered in vertical 9:16 format with word by word karaoke captions. That is how you turn a single interview into ten viral short clips.');
    Start-Sleep -Milliseconds 500;
    $synth.Speak('Adopt this multimodal clipping pipeline today, and transform your content strategy forever.');
    $synth.Dispose();
    """
    cmd = ["powershell", "-NoProfile", "-Command", script]
    subprocess.run(cmd, check=True)
    return wav_path


def get_audio_duration(wav_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(wav_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def render_sample_video(output_mp4: Path, duration: float, fps: int = 25, width: int = 1280, height: int = 720):
    """
    Renders synthetic video containing a clearly detectable human face
    with speaker motion and visual slides to test OpenCV face detection and reframe.
    """
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    raw_video_path = TEMP_DIR / "raw_visual.mp4"
    out = cv2.VideoWriter(str(raw_video_path), fourcc, fps, (width, height))

    total_frames = int(duration * fps)

    # Face parameters (positioned slightly left-of-center to test 9:16 speaker centering)
    face_cx = int(width * 0.42)
    face_cy = int(height * 0.45)
    face_radius = int(height * 0.22)

    for f in range(total_frames):
        t = f / fps
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Gradient background (deep slate to navy)
        for y in range(height):
            ratio = y / height
            frame[y, :] = (int(35 + 20 * ratio), int(22 + 15 * ratio), int(16 + 10 * ratio))

        # Dynamic floating elements / slides
        slide_text = "OPUS CLIP MULTIMODAL AI"
        if t < 15.0:
            slide_sub = "THE VIRAL SHORT-FORM SECRET"
        elif t < 35.0:
            slide_sub = "VISION + AUDIO + TRANSCRIPT FUSION"
        elif t < 55.0:
            slide_sub = "9:16 VERTICAL AUTO-REFRAME & KARAOKE"
        else:
            slide_sub = "SCALE YOUR CONTENT 10X"

        # Draw banner at top
        cv2.rectangle(frame, (60, 40), (width - 60, 110), (55, 35, 25), -1)
        cv2.putText(frame, slide_text, (85, 85), cv2.FONT_HERSHEY_DUPLEX, 1.0, (230, 240, 255), 2)

        # Draw subtitle badge
        cv2.putText(frame, slide_sub, (85, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 215, 255), 2)

        # Draw Realistic Detectable Face:
        # Subtle speaker head bobbing
        bob_x = int(12 * np.sin(t * 1.8))
        bob_y = int(8 * np.sin(t * 3.6))
        cx = face_cx + bob_x
        cy = face_cy + bob_y

        # Shoulders/body
        cv2.ellipse(frame, (cx, cy + int(face_radius * 1.5)), (int(face_radius * 1.4), int(face_radius * 0.9)), 0, 0, 180, (70, 45, 30), -1)

        # Head / Face oval (skin tone BGR)
        skin_color = (180, 205, 240)
        cv2.ellipse(frame, (cx, cy), (int(face_radius * 0.75), int(face_radius * 0.95)), 0, 0, 360, skin_color, -1)

        # Eyes
        eye_y = cy - int(face_radius * 0.18)
        left_eye_x = cx - int(face_radius * 0.28)
        right_eye_x = cx + int(face_radius * 0.28)
        eye_r = int(face_radius * 0.09)

        # Sclera (white)
        cv2.circle(frame, (left_eye_x, eye_y), eye_r, (255, 255, 255), -1)
        cv2.circle(frame, (right_eye_x, eye_y), eye_r, (255, 255, 255), -1)
        # Pupils
        cv2.circle(frame, (left_eye_x, eye_y), int(eye_r * 0.5), (40, 30, 20), -1)
        cv2.circle(frame, (right_eye_x, eye_y), int(eye_r * 0.5), (40, 30, 20), -1)

        # Eyebrows
        cv2.line(frame, (left_eye_x - eye_r, eye_y - 12), (left_eye_x + eye_r, eye_y - 10), (30, 20, 15), 3)
        cv2.line(frame, (right_eye_x - eye_r, eye_y - 10), (right_eye_x + eye_r, eye_y - 12), (30, 20, 15), 3)

        # Nose
        nose_top = (cx, eye_y + 8)
        nose_bottom = (cx - 4, cy + int(face_radius * 0.12))
        cv2.line(frame, nose_top, nose_bottom, (140, 160, 200), 2)
        cv2.line(frame, nose_bottom, (cx + 5, cy + int(face_radius * 0.12)), (140, 160, 200), 2)

        # Animated Mouth (open/close based on speech wave)
        mouth_open = int(8 + 7 * abs(np.sin(t * 8.0)))
        mouth_y = cy + int(face_radius * 0.38)
        cv2.ellipse(frame, (cx, mouth_y), (int(face_radius * 0.26), mouth_open), 0, 0, 360, (50, 40, 120), -1)

        # Hair
        cv2.ellipse(frame, (cx, cy - int(face_radius * 0.5)), (int(face_radius * 0.8), int(face_radius * 0.45)), 0, 180, 360, (30, 20, 15), -1)

        # Realtime timestamp display
        cv2.putText(frame, f"TIME: {t:04.1f}s", (width - 240, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

        out.write(frame)

    out.release()
    return raw_video_path


def build_sample_test_video(output_path: Path) -> Path:
    """Generate complete sample video with synchronized speech audio."""
    ensure_dirs()
    wav_path = TEMP_DIR / "sample_speech.wav"
    print("[*] Generating speech audio track...")
    create_sample_speech_wav(wav_path)

    dur = get_audio_duration(wav_path)
    print(f"[*] Speech audio duration: {dur:.2f}s")

    print(f"[*] Rendering sample video frames ({dur:.1f}s)...")
    raw_mp4 = render_sample_video(output_path, duration=dur, fps=25)

    print("[*] Muxing video and audio with ffmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_mp4),
        "-i", str(wav_path),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"[+] Sample test video created at: {output_path.resolve()}")
    return output_path


if __name__ == "__main__":
    out_file = TEMP_DIR / "sample_podcast.mp4"
    build_sample_test_video(out_file)
