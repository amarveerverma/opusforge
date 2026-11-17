# ClipForge — REST API Specification

**Base URL**: `http://localhost:8000`  
**Protocol**: HTTP/1.1 + Server-Sent Events (SSE)  
**Content-Type**: `application/json` (unless `multipart/form-data` for uploads)  

---

## 1. System & Health Endpoints

### `GET /health`
- **Description**: Lightweight health probe to verify FastAPI server is running.
- **Response**:
```json
{
  "status": "healthy",
  "app": "ClipForge",
  "version": "1.0.0"
}
```

### `GET /system/status`
- **Description**: Returns live host hardware metrics (GPU VRAM, GPU util, CPU, RAM, Disk).
- **Response**:
```json
{
  "gpu": {
    "name": "NVIDIA GeForce RTX 4060 Laptop GPU",
    "vram_total_mb": 8188,
    "vram_used_mb": 420,
    "vram_free_mb": 7768,
    "utilization_percent": 2,
    "temperature_c": 41
  },
  "ram": {
    "total_gb": 16.0,
    "free_gb": 4.3,
    "used_percent": 73.1
  },
  "disk": {
    "free_gb": 612.4,
    "total_gb": 1002.5
  },
  "encoders": ["h264_nvenc", "hevc_nvenc", "av1_nvenc", "libx264"]
}
```

---

## 2. Project Endpoints

### `POST /projects`
- **Description**: Create a new project record.
- **Request Body**:
```json
{
  "title": "Lex Fridman AI Interview",
  "instructions": "Find 5 high-impact clips between 30 and 60 seconds with strong hooks"
}
```
- **Response**: `201 Created` with project object.

### `POST /projects/{project_id}/upload`
- **Description**: Upload a source video file (`multipart/form-data`).
- **Response**:
```json
{
  "project_id": "proj_abc123",
  "filename": "interview.mp4",
  "duration": 1824.5,
  "width": 1920,
  "height": 1080,
  "fps": 30.0,
  "codec": "h264",
  "thumbnail_url": "/projects/proj_abc123/thumbnail"
}
```

### `GET /projects`
- **Description**: List all projects, ordered by creation date desc.

### `GET /projects/{project_id}`
- **Description**: Get full project details, including source media, jobs, and associated clips.

### `DELETE /projects/{project_id}`
- **Description**: Delete project metadata and generated artifacts (original source file optionally retained).

---

## 3. Analysis & Job Pipeline Endpoints

### `POST /projects/{project_id}/analyze`
- **Description**: Triggers the AI pipeline (transcription, diarization, scene detection, clip discovery).
- **Request Body**:
```json
{
  "min_duration": 30.0,
  "max_duration": 60.0,
  "target_clips": 5,
  "language": "en",
  "model_profile": "balanced"
}
```
- **Response**:
```json
{
  "job_id": "job_xyz789",
  "project_id": "proj_abc123",
  "status": "pending",
  "message": "Analysis pipeline queued"
}
```

### `GET /jobs/{job_id}`
- **Description**: Poll job progress and status.

### `GET /jobs/{job_id}/events`
- **Description**: Real-time Server-Sent Events (SSE) streaming live progress percentages, current stage, and log messages.

### `POST /jobs/{job_id}/cancel`
- **Description**: Safely cancels a running pipeline job and releases GPU memory.

---

## 4. Clips & Editing Endpoints

### `GET /projects/{project_id}/clips`
- **Description**: List discovered clips ranked by virality score.

### `GET /clips/{clip_id}`
- **Description**: Get single clip details, transcript, score breakdown, and framing parameters.

### `PATCH /clips/{clip_id}`
- **Description**: Update clip parameters (boundary times, title, crop mode, caption style).
- **Request Body**:
```json
{
  "start_time": 45.2,
  "end_time": 92.8,
  "title": "Why AGI is closer than you think",
  "crop_config": {
    "mode": "auto_face",
    "manual_x_offset": null
  },
  "caption_config": {
    "preset": "hormozi",
    "font_size": 52,
    "highlight_color": "#00FF00"
  }
}
```

---

## 5. Rendering & Export Endpoints

### `POST /clips/{clip_id}/render`
- **Description**: Render final 1080x1920 MP4 via hardware NVENC.
- **Response**:
```json
{
  "render_id": "rend_456",
  "status": "completed",
  "output_path": "/data/projects/proj_abc123/renders/clip_1.mp4",
  "render_duration_s": 4.8,
  "file_size_mb": 42.1
}
```

### `GET /renders/{render_id}/download`
- **Description**: Stream rendered MP4 file for browser download.

### `POST /renders/{render_id}/reveal`
- **Description**: Opens Windows File Explorer with the rendered video file highlighted.
