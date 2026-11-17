import os
import re
import json
import uuid
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from ..database import get_db
from ..config import settings
from ..core.subtitles import generate_ass_file
from ..core.reframer import calculate_clip_framing
from ..core.renderer import render_clip, RenderResult

router = APIRouter(tags=["Renders"])
logger = logging.getLogger("clipforge.renders")

class RenderResponse(BaseModel):
    id: str
    clip_id: str
    project_id: str
    output_file_path: str
    width: int
    height: int
    fps: float
    duration: float
    file_size_bytes: int
    encoder_used: str
    quality_report: Optional[Dict[str, Any]] = None
    created_at: str

@router.post("/clips/{clip_id}/render", response_model=RenderResponse)
async def trigger_clip_render(clip_id: str):
    """
    Renders a vertical 9:16 short with dynamic karaoke animated subtitles,
    subject-aware framing, and NVENC GPU hardware acceleration.
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
        clip = await cursor.fetchone()
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
            
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (clip["project_id"],))
        proj = await cursor.fetchone()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
            
    source_video_path = Path(proj["source_file_path"])
    if not source_video_path.exists():
        raise HTTPException(status_code=400, detail="Source video file not found on disk")
        
    proj_dir = settings.PROJECTS_DIR / clip["project_id"]
    renders_dir = proj_dir / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Prepare word timings from transcript.json
    words: List[Dict[str, Any]] = []
    transcript_file = proj_dir / "transcripts" / "transcript.json"
    if transcript_file.exists():
        try:
            transcript_data = json.loads(transcript_file.read_text(encoding="utf-8"))
            for seg in transcript_data.get("segments", []):
                for w in seg.get("words", []):
                    words.append(w)
        except Exception as e:
            logger.warning("Could not read transcript words for ASS subtitles: %s", e)
            
    # 2. Generate ASS Subtitle File
    caption_cfg = json.loads(clip["caption_config_json"]) if clip["caption_config_json"] else {}
    preset_name = caption_cfg.get("preset", "mrbeast")
    ass_file = renders_dir / f"{clip_id}_subtitles.ass"
    
    if words:
        generate_ass_file(
            words=words,
            clip_start=clip["start_time"],
            clip_end=clip["end_time"],
            output_path=ass_file,
            preset_name=preset_name,
            custom_config=caption_cfg,
        )
    else:
        ass_file = None
        
    # 3. Determine 9:16 Crop Configuration
    crop_cfg = json.loads(clip["crop_config_json"]) if clip["crop_config_json"] else None
    if not crop_cfg or not crop_cfg.get("crop_w"):
        source_w = proj["width"] if proj["width"] > 0 else 1920
        source_h = proj["height"] if proj["height"] > 0 else 1080
        face_file = proj_dir / "analysis" / "face_tracks.json"
        face_data = json.loads(face_file.read_text(encoding="utf-8")) if face_file.exists() else None
        calculated_cfg = calculate_clip_framing(
            source_width=source_w,
            source_height=source_h,
            clip_start=clip["start_time"],
            clip_end=clip["end_time"],
            face_data=face_data,
            mode="smart_track",
        )
        crop_cfg = calculated_cfg.model_dump()
        
    # 4. Render Video via FFmpeg NVENC
    output_video_path = renders_dir / f"{clip_id}.mp4"
    result: RenderResult = render_clip(
        source_video=source_video_path,
        start_time=clip["start_time"],
        end_time=clip["end_time"],
        output_path=output_video_path,
        crop_config=crop_cfg,
        ass_path=ass_file,
        use_nvenc=True,
    )
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Video rendering failed: {result.error_message}"
        )
        
    # 5. Persist render record in SQLite
    render_id = f"rnd_{uuid.uuid4().hex[:10]}"
    quality_report = {
        "render_time_seconds": result.render_time_seconds,
        "encoder": result.encoder_used,
        "file_size_mb": round(result.file_size_bytes / (1024 * 1024), 2),
        "target_resolution": f"{result.width}x{result.height}",
    }
    
    async with get_db() as db:
        # Delete prior render for this clip if exists
        await db.execute("DELETE FROM renders WHERE clip_id = ?", (clip_id,))
        await db.execute(
            """
            INSERT INTO renders (
                id, clip_id, project_id, output_file_path, width, height,
                fps, duration, file_size_bytes, encoder_used, quality_report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                render_id,
                clip_id,
                clip["project_id"],
                result.output_path,
                result.width,
                result.height,
                result.fps,
                result.duration,
                result.file_size_bytes,
                result.encoder_used,
                json.dumps(quality_report),
            )
        )
        await db.execute("UPDATE clips SET status = 'rendered' WHERE id = ?", (clip_id,))
        await db.commit()
        
    return await get_render_info(render_id)

@router.get("/clips/{clip_id}/render", response_model=RenderResponse)
async def get_clip_render(clip_id: str):
    """Retrieves the render record for a clip if it has already been rendered."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM renders WHERE clip_id = ? ORDER BY created_at DESC LIMIT 1", (clip_id,))
        row = await cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="No render exists for this clip")
        
    return RenderResponse(
        id=row["id"],
        clip_id=row["clip_id"],
        project_id=row["project_id"],
        output_file_path=row["output_file_path"],
        width=row["width"],
        height=row["height"],
        fps=row["fps"],
        duration=row["duration"],
        file_size_bytes=row["file_size_bytes"],
        encoder_used=row["encoder_used"],
        quality_report=json.loads(row["quality_report_json"]) if row["quality_report_json"] else {},
        created_at=str(row["created_at"]),
    )

@router.get("/renders/{render_id}", response_model=RenderResponse)
async def get_render_info(render_id: str):
    """Retrieves render metadata including file specs and quality report."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM renders WHERE id = ?", (render_id,))
        row = await cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Render not found")
        
    return RenderResponse(
        id=row["id"],
        clip_id=row["clip_id"],
        project_id=row["project_id"],
        output_file_path=row["output_file_path"],
        width=row["width"],
        height=row["height"],
        fps=row["fps"],
        duration=row["duration"],
        file_size_bytes=row["file_size_bytes"],
        encoder_used=row["encoder_used"],
        quality_report=json.loads(row["quality_report_json"]) if row["quality_report_json"] else {},
        created_at=str(row["created_at"]),
    )

@router.get("/projects/{project_id}/renders", response_model=List[RenderResponse])
async def list_project_renders(project_id: str):
    """Lists all rendered clips for a project."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM renders WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        rows = await cursor.fetchall()
        
    renders = []
    for r in rows:
        renders.append(RenderResponse(
            id=r["id"],
            clip_id=r["clip_id"],
            project_id=r["project_id"],
            output_file_path=r["output_file_path"],
            width=r["width"],
            height=r["height"],
            fps=r["fps"],
            duration=r["duration"],
            file_size_bytes=r["file_size_bytes"],
            encoder_used=r["encoder_used"],
            quality_report=json.loads(r["quality_report_json"]) if r["quality_report_json"] else {},
            created_at=str(r["created_at"]),
        ))
    return renders

@router.get("/renders/{render_id}/download")
async def download_render(render_id: str):
    """Streams the rendered MP4 video file to the client for download."""
    async with get_db() as db:
        cursor = await db.execute("SELECT output_file_path FROM renders WHERE id = ?", (render_id,))
        row = await cursor.fetchone()
        
    if not row or not os.path.exists(row["output_file_path"]):
        raise HTTPException(status_code=404, detail="Render file not found on disk")
        
    return FileResponse(
        path=row["output_file_path"],
        media_type="video/mp4",
        filename=Path(row["output_file_path"]).name
    )

@router.get("/renders/{render_id}/stream")
async def stream_render_video(render_id: str, request: Request):
    """
    Streams the rendered 9:16 video with HTTP Range Requests (Status 206 Partial Content)
    enabling instant seeking in HTML5 video players on the website.
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT output_file_path FROM renders WHERE id = ?", (render_id,))
        row = await cursor.fetchone()
        
    if not row or not os.path.exists(row["output_file_path"]):
        raise HTTPException(status_code=404, detail="Render video not found")
        
    path = Path(row["output_file_path"])
    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    
    if not range_header:
        return FileResponse(
            str(path),
            media_type="video/mp4",
            headers={"Accept-Ranges": "bytes"}
        )
        
    range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        raise HTTPException(status_code=416, detail="Invalid Range Header")
        
    start = int(range_match.group(1))
    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
    
    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(status_code=416, detail="Requested range not satisfiable")
        
    chunk_size = (end - start) + 1
    
    def iter_file_chunk():
        with open(path, "rb") as video:
            video.seek(start)
            remaining = chunk_size
            while remaining > 0:
                read_bytes = min(remaining, 1024 * 512)
                data = video.read(read_bytes)
                if not data:
                    break
                remaining -= len(data)
                yield data
                
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(iter_file_chunk(), status_code=206, headers=headers)

@router.post("/renders/{render_id}/reveal")
async def reveal_render_in_explorer(render_id: str):
    """Opens Windows Explorer with the rendered file highlighted."""
    async with get_db() as db:
        cursor = await db.execute("SELECT output_file_path FROM renders WHERE id = ?", (render_id,))
        row = await cursor.fetchone()
        
    if not row or not os.path.exists(row["output_file_path"]):
        raise HTTPException(status_code=404, detail="Render file not found")
        
    abs_path = os.path.abspath(row["output_file_path"])
    subprocess.run(["explorer.exe", f"/select,{abs_path}"], check=False)
    return {"status": "success", "revealed": abs_path}
