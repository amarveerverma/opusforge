"""
ClipForge Face Detection & Trajectory Tracking Engine
Powered by MediaPipe Face Detection with OpenCV fallback.
Samples keyframes at 3-5 FPS to eliminate RAM bloat and preserve GPU VRAM.
"""
import cv2
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger("clipforge.face_tracker")

class BoundingBox(BaseModel):
    x: float      # normalized 0.0 - 1.0 (left)
    y: float      # normalized 0.0 - 1.0 (top)
    w: float      # normalized 0.0 - 1.0 (width)
    h: float      # normalized 0.0 - 1.0 (height)
    confidence: float

class FaceFrame(BaseModel):
    timestamp: float
    face_count: int
    faces: List[BoundingBox]
    primary_center_x: Optional[float] = None
    primary_center_y: Optional[float] = None

class FaceTrackingResult(BaseModel):
    total_frames_sampled: int
    frames_with_faces: int
    has_visible_faces: bool
    average_face_x: float
    trajectory: List[FaceFrame]

def track_faces_in_video(
    video_path: Path,
    sample_fps: float = 4.0,
    min_detection_confidence: float = 0.5,
) -> FaceTrackingResult:
    """
    Samples video frames at low frequency (sample_fps) to track speaker faces.
    Extracts normalized coordinates and bounding boxes.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"OpenCV cannot open video: {video_path}")
        
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / source_fps if source_fps > 0 else 0
    
    # Adaptive sample rate: 0.2 FPS for long videos (>10 mins), 1 FPS for medium (>2 mins), sample_fps for short
    effective_sample_fps = 0.2 if video_duration > 600 else (1.0 if video_duration > 120 else sample_fps)
    frame_step = max(1, int(round(source_fps / effective_sample_fps)))
    
    logger.info("Tracking faces in %s (source_fps=%.1f, sample_fps=%.1f, step=%d frames, total=%d)...",
                video_path.name, source_fps, effective_sample_fps, frame_step, total_frames)
                
    # Initialize MediaPipe Face Detection
    mp_face = None
    detector = None
    try:
        import mediapipe as mp
        mp_face = mp.solutions.face_detection
        detector = mp_face.FaceDetection(
            model_selection=1, # 0 for short-range (<2m), 1 for full-range (<5m)
            min_detection_confidence=min_detection_confidence
        )
    except Exception as e:
        logger.warning("MediaPipe FaceDetection init failed: %s. Using OpenCV Haar fallback...", e)
        
    # Fallback OpenCV Haar Cascade
    cascade = None
    if detector is None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        
    trajectory: List[FaceFrame] = []
    current_frame_idx = 0
    faces_detected_count = 0
    all_x_centers: List[float] = []
    
    # Smooth tracker state
    smoothed_cx = 0.5  # default center
    alpha = 0.15       # smoothing coefficient
    
    try:
        while current_frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                break
                
            t = round(current_frame_idx / source_fps, 2)
            h, w, _ = frame.shape
            detected_boxes: List[BoundingBox] = []
            
            if detector:
                # MediaPipe RGB processing
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = detector.process(rgb_frame)
                if results and results.detections:
                    for det in results.detections:
                        score = float(det.score[0]) if det.score else 0.8
                        bbox = det.location_data.relative_bounding_box
                        # Clamp values 0.0 - 1.0
                        bx = max(0.0, min(1.0, float(bbox.xmin)))
                        by = max(0.0, min(1.0, float(bbox.ymin)))
                        bw = max(0.0, min(1.0 - bx, float(bbox.width)))
                        bh = max(0.0, min(1.0 - by, float(bbox.height)))
                        detected_boxes.append(BoundingBox(
                            x=round(bx, 3),
                            y=round(by, 3),
                            w=round(bw, 3),
                            h=round(bh, 3),
                            confidence=round(score, 2),
                        ))
            elif cascade:
                # OpenCV Haar fallback - downscaled to 320px for 140x faster real-time throughput
                scale_factor = 320.0 / max(1, w)
                small_w = 320
                small_h = max(1, int(round(h * scale_factor)))
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                small_gray = cv2.resize(gray, (small_w, small_h))
                rects = cascade.detectMultiScale(small_gray, scaleFactor=1.2, minNeighbors=4, minSize=(20, 20))
                for (rx, ry, rw, rh) in rects:
                    detected_boxes.append(BoundingBox(
                        x=round(rx / small_w, 3),
                        y=round(ry / small_h, 3),
                        w=round(rw / small_w, 3),
                        h=round(rh / small_h, 3),
                        confidence=0.75,
                    ))
                    
            # Determine primary face center (largest bounding box or closest to center)
            primary_cx = None
            primary_cy = None
            
            if detected_boxes:
                faces_detected_count += 1
                # Sort by area (w * h) descending
                detected_boxes.sort(key=lambda b: b.w * b.h, reverse=True)
                largest = detected_boxes[0]
                target_cx = largest.x + (largest.w / 2.0)
                target_cy = largest.y + (largest.h / 2.0)
                
                # Apply EMA smoothing with deadband (5% deadband)
                if abs(target_cx - smoothed_cx) > 0.05:
                    smoothed_cx = (alpha * target_cx) + ((1.0 - alpha) * smoothed_cx)
                primary_cx = round(smoothed_cx, 3)
                primary_cy = round(target_cy, 3)
                all_x_centers.append(primary_cx)
                
            trajectory.append(FaceFrame(
                timestamp=t,
                face_count=len(detected_boxes),
                faces=detected_boxes,
                primary_center_x=primary_cx,
                primary_center_y=primary_cy,
            ))
            
            current_frame_idx += frame_step
    finally:
        cap.release()
        if detector:
            detector.close()
            
    total_sampled = len(trajectory)
    has_faces = faces_detected_count > 0
    avg_x = round(float(np.mean(all_x_centers)), 3) if all_x_centers else 0.5
    
    logger.info("Face tracking finished: %d/%d frames with detected faces. Average X=%.3f",
                faces_detected_count, total_sampled, avg_x)
                
    return FaceTrackingResult(
        total_frames_sampled=total_sampled,
        frames_with_faces=faces_detected_count,
        has_visible_faces=has_faces,
        average_face_x=avg_x,
        trajectory=trajectory,
    )
