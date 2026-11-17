from fastapi import APIRouter, HTTPException
from ..schemas.job import JobResponse
from ..database import get_db

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Retrieves status and progress of a background processing job."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return JobResponse(
        id=row["id"],
        project_id=row["project_id"],
        stage=row["stage"],
        progress=row["progress"],
        status=row["status"],
        error_message=row["error_message"],
        started_at=str(row["started_at"]) if row["started_at"] else None,
        completed_at=str(row["completed_at"]) if row["completed_at"] else None
    )

@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: str):
    """Cancels a job and updates its status to cancelled."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
            
        await db.execute("UPDATE jobs SET status = 'cancelled' WHERE id = ?", (job_id,))
        await db.commit()
        
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        updated = await cursor.fetchone()
        
    return JobResponse(
        id=updated["id"],
        project_id=updated["project_id"],
        stage=updated["stage"],
        progress=updated["progress"],
        status=updated["status"],
        error_message=updated["error_message"],
        started_at=str(updated["started_at"]) if updated["started_at"] else None,
        completed_at=str(updated["completed_at"]) if updated["completed_at"] else None
    )
