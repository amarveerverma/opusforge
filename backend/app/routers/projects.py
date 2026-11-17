import os
import re
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from ..schemas.project import ProjectCreate, ProjectResponse, ProjectListResponse
from ..database import get_db
from ..config import settings
from ..core.ingestion import (
    validate_video_file,
    generate_thumbnails,
    save_upload_stream,
    SUPPORTED_EXTENSIONS,
)

router = APIRouter(prefix="/projects", tags=["Projects"])
logger = logging.getLogger("clipforge.projects")

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(payload: ProjectCreate):
    """Creates a new project record and allocates its local folder structure."""
    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    
    # Create project storage directory layout
    proj_dir = settings.PROJECTS_DIR / project_id
    (proj_dir / "source").mkdir(parents=True, exist_ok=True)
    (proj_dir / "thumbnails").mkdir(parents=True, exist_ok=True)
    (proj_dir / "transcripts").mkdir(parents=True, exist_ok=True)
    (proj_dir / "analysis").mkdir(parents=True, exist_ok=True)
    (proj_dir / "candidates").mkdir(parents=True, exist_ok=True)
    (proj_dir / "renders").mkdir(parents=True, exist_ok=True)
    
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO projects (id, title, original_filename, source_file_path, instructions, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, payload.title, "pending_upload", "", payload.instructions, "created", now, now)
        )
        await db.commit()
        
    return ProjectResponse(
        id=project_id,
        title=payload.title,
        original_filename="pending_upload",
        source_file_path="",
        duration=0.0,
        width=0,
        height=0,
        fps=0.0,
        instructions=payload.instructions,
        status="created",
        created_at=now,
        updated_at=now,
        clips_count=0
    )

@router.get("", response_model=ProjectListResponse)
async def list_projects():
    """Lists all user projects ordered by newest first."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT p.*, (SELECT COUNT(*) FROM clips c WHERE c.project_id = p.id) as clips_count
            FROM projects p
            ORDER BY p.created_at DESC
            """
        )
        rows = await cursor.fetchall()
        
    projects = []
    for r in rows:
        projects.append(ProjectResponse(
            id=r["id"],
            title=r["title"],
            original_filename=r["original_filename"],
            source_file_path=r["source_file_path"],
            duration=r["duration"] or 0.0,
            width=r["width"] or 0,
            height=r["height"] or 0,
            fps=r["fps"] or 0.0,
            codec=r["codec"],
            instructions=r["instructions"],
            status=r["status"],
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
            clips_count=r["clips_count"]
        ))
        
    return ProjectListResponse(projects=projects, total=len(projects))

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Retrieves full metadata for a single project."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT p.*, (SELECT COUNT(*) FROM clips c WHERE c.project_id = p.id) as clips_count
            FROM projects p
            WHERE p.id = ?
            """,
            (project_id,)
        )
        row = await cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return ProjectResponse(
        id=row["id"],
        title=row["title"],
        original_filename=row["original_filename"],
        source_file_path=row["source_file_path"],
        duration=row["duration"] or 0.0,
        width=row["width"] or 0,
        height=row["height"] or 0,
        fps=row["fps"] or 0.0,
        codec=row["codec"],
        instructions=row["instructions"],
        status=row["status"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        clips_count=row["clips_count"]
    )

@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """Deletes a project record from SQLite."""
    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
            
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
        
    return None

@router.post("/{project_id}/upload", response_model=ProjectResponse)
async def upload_video(project_id: str, file: UploadFile = File(...)):
    """
    Accepts video upload, validates format, runs FFprobe inspection,
    generates multi-timestamp thumbnails, and updates project status to ready.
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = await cursor.fetchone()
        
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Sanitize filename
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename or "video.mp4")
    file_ext = Path(safe_name).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{file_ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
        
    proj_dir = settings.PROJECTS_DIR / project_id
    dest_path = proj_dir / "source" / safe_name
    
    # 1. Stream upload to disk (chunked)
    try:
        bytes_written = await save_upload_stream(file, dest_path)
        logger.info("Saved %d bytes to %s", bytes_written, dest_path)
    except Exception as e:
        logger.error("Failed to stream upload: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")
        
    # 2. Validate and extract metadata via FFprobe
    try:
        meta = validate_video_file(dest_path)
    except ValueError as e:
        # Cleanup invalid file
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))
        
    # 3. Generate Thumbnails
    thumbs_dir = proj_dir / "thumbnails"
    try:
        generate_thumbnails(dest_path, thumbs_dir)
    except Exception as e:
        logger.warning("Thumbnail generation warning for %s: %s", project_id, e)
        
    # 4. Update SQLite project record
    now = datetime.utcnow().isoformat()
    async with get_db() as db:
        await db.execute(
            """
            UPDATE projects
            SET original_filename = ?, source_file_path = ?, duration = ?, width = ?, height = ?, fps = ?, codec = ?, status = 'ready', updated_at = ?
            WHERE id = ?
            """,
            (
                file.filename or safe_name,
                str(dest_path),
                meta.duration,
                meta.width,
                meta.height,
                meta.fps,
                meta.video_codec,
                now,
                project_id,
            )
        )
        await db.commit()
        
    return await get_project(project_id)

@router.get("/{project_id}/thumbnail")
async def get_project_thumbnail(project_id: str, index: int = 0):
    """Serves the generated thumbnail for the project."""
    proj_dir = settings.PROJECTS_DIR / project_id / "thumbnails"
    thumb_path = proj_dir / f"thumb_{index}.jpg"
    
    if not thumb_path.exists():
        # Fallback to any existing thumbnail
        existing = list(proj_dir.glob("*.jpg"))
        if existing:
            thumb_path = existing[0]
        else:
            raise HTTPException(status_code=404, detail="Thumbnail not found")
            
    return FileResponse(
        path=str(thumb_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"}
    )

@router.get("/{project_id}/stream")
async def stream_project_video(project_id: str, request: Request):
    """
    Streams project video with HTTP Range Requests (Status 206 Partial Content)
    enabling instant seeking in HTML5 video players.
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT source_file_path FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        
    if not row or not row["source_file_path"] or not os.path.exists(row["source_file_path"]):
        raise HTTPException(status_code=404, detail="Source video not found")
        
    path = Path(row["source_file_path"])
    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    
    if not range_header:
        # Full content response
        return FileResponse(
            str(path),
            media_type="video/mp4",
            headers={"Accept-Ranges": "bytes"}
        )
        
    # Parse Range: bytes=start-end
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
    
    return StreamingResponse(
        iter_file_chunk(),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )
