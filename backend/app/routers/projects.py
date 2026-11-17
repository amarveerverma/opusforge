import uuid
import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional, List
from ..schemas.project import ProjectCreate, ProjectResponse, ProjectListResponse
from ..database import get_db
from ..config import settings
import aiofiles

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
