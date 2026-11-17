import os
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..database import get_db

router = APIRouter(prefix="/renders", tags=["Renders"])

@router.get("/{render_id}")
async def get_render_info(render_id: str):
    """Retrieves render metadata including file specs and quality report."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM renders WHERE id = ?", (render_id,))
        row = await cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Render not found")
        
    return dict(row)

@router.get("/{render_id}/download")
async def download_render(render_id: str):
    """Streams the rendered MP4 video file to the client."""
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

@router.post("/{render_id}/reveal")
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
