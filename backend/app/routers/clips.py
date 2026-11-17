import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from ..schemas.clip import ClipResponse, ClipUpdate
from ..database import get_db
from ..config import settings
from ..core.clip_discovery import discover_clips_from_analysis, CandidateClip

router = APIRouter(tags=["Clips"])

@router.post("/projects/{project_id}/discover", response_model=List[ClipResponse])
async def discover_project_clips(project_id: str):
    """
    Executes AI clip discovery by fusing transcripts, scene cuts, face presence,
    and user instructions into ranked, non-overlapping candidate moments.
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        proj = await cursor.fetchone()
        
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    proj_dir = settings.PROJECTS_DIR / project_id
    transcript_file = proj_dir / "transcripts" / "transcript.json"
    if not transcript_file.exists():
        raise HTTPException(status_code=400, detail="Project has not been transcribed yet. Run transcription first.")
        
    transcript_data = json.loads(transcript_file.read_text(encoding="utf-8"))
    
    scene_file = proj_dir / "analysis" / "scenes.json"
    scene_data = json.loads(scene_file.read_text(encoding="utf-8")) if scene_file.exists() else None
    
    face_file = proj_dir / "analysis" / "face_tracks.json"
    face_data = json.loads(face_file.read_text(encoding="utf-8")) if face_file.exists() else None
    
    candidates = discover_clips_from_analysis(
        project_id=project_id,
        transcript_data=transcript_data,
        scene_data=scene_data,
        face_data=face_data,
        instructions=proj["instructions"],
    )
    
    # Save candidate clips to candidates.json
    cand_dir = proj_dir / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    (cand_dir / "candidates.json").write_text(
        json.dumps([c.model_dump() for c in candidates], indent=2),
        encoding="utf-8"
    )
    
    # Insert or replace in SQLite clips table
    async with get_db() as db:
        await db.execute("DELETE FROM clips WHERE project_id = ? AND status = 'suggested'", (project_id,))
        
        for c in candidates:
            await db.execute(
                """
                INSERT INTO clips (
                    id, project_id, rank, start_time, end_time, duration,
                    title, hook, summary, virality_score, letter_grade,
                    score_breakdown_json, transcript_excerpt, crop_config_json,
                    caption_config_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'suggested')
                """,
                (
                    c.clip_id,
                    project_id,
                    c.rank,
                    c.start_time,
                    c.end_time,
                    c.duration,
                    c.title,
                    c.hook,
                    c.summary,
                    c.virality_score,
                    c.letter_grade,
                    json.dumps(c.score_breakdown.model_dump()),
                    c.transcript_excerpt,
                    json.dumps(c.crop_config),
                    json.dumps(c.caption_config),
                )
            )
        await db.execute("UPDATE projects SET status = 'discovered' WHERE id = ?", (project_id,))
        await db.commit()
        
    return await list_project_clips(project_id)

@router.get("/projects/{project_id}/clips", response_model=List[ClipResponse])
async def list_project_clips(project_id: str):
    """Lists all clips belonging to a specific project, ordered by rank."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT c.*, (SELECT id FROM renders r WHERE r.clip_id = c.id LIMIT 1) as render_id
            FROM clips c
            WHERE c.project_id = ?
            ORDER BY c.rank ASC, c.virality_score DESC
            """,
            (project_id,)
        )
        rows = await cursor.fetchall()
        
    clips = []
    for r in rows:
        score_breakdown = json.loads(r["score_breakdown_json"]) if r["score_breakdown_json"] else {}
        crop_config = json.loads(r["crop_config_json"]) if r["crop_config_json"] else {}
        caption_config = json.loads(r["caption_config_json"]) if r["caption_config_json"] else {}
        
        clips.append(ClipResponse(
            id=r["id"],
            project_id=r["project_id"],
            rank=r["rank"],
            start_time=r["start_time"],
            end_time=r["end_time"],
            duration=r["duration"],
            title=r["title"],
            hook=r["hook"],
            summary=r["summary"],
            virality_score=r["virality_score"],
            letter_grade=r["letter_grade"],
            score_breakdown=score_breakdown,
            transcript_excerpt=r["transcript_excerpt"],
            crop_config=crop_config,
            caption_config=caption_config,
            status=r["status"],
            created_at=str(r["created_at"]),
            rendered=bool(r["render_id"]),
            render_id=r["render_id"]
        ))
    return clips

@router.get("/clips/{clip_id}", response_model=ClipResponse)
async def get_clip(clip_id: str):
    """Retrieves full details for a single clip."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT c.*, (SELECT id FROM renders r WHERE r.clip_id = c.id LIMIT 1) as render_id
            FROM clips c
            WHERE c.id = ?
            """,
            (clip_id,)
        )
        r = await cursor.fetchone()
        
    if not r:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    return ClipResponse(
        id=r["id"],
        project_id=r["project_id"],
        rank=r["rank"],
        start_time=r["start_time"],
        end_time=r["end_time"],
        duration=r["duration"],
        title=r["title"],
        hook=r["hook"],
        summary=r["summary"],
        virality_score=r["virality_score"],
        letter_grade=r["letter_grade"],
        score_breakdown=json.loads(r["score_breakdown_json"]) if r["score_breakdown_json"] else {},
        transcript_excerpt=r["transcript_excerpt"],
        crop_config=json.loads(r["crop_config_json"]) if r["crop_config_json"] else {},
        caption_config=json.loads(r["caption_config_json"]) if r["caption_config_json"] else {},
        status=r["status"],
        created_at=str(r["created_at"]),
        rendered=bool(r["render_id"]),
        render_id=r["render_id"]
    )

@router.patch("/clips/{clip_id}", response_model=ClipResponse)
async def update_clip(clip_id: str, payload: ClipUpdate):
    """Updates clip parameters such as title, trim boundaries, framing, or caption styles."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
        r = await cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Clip not found")
            
        new_title = payload.title if payload.title is not None else r["title"]
        new_start = payload.start_time if payload.start_time is not None else r["start_time"]
        new_end = payload.end_time if payload.end_time is not None else r["end_time"]
        new_duration = round(new_end - new_start, 2)
        
        new_crop = json.dumps(payload.crop_config) if payload.crop_config is not None else r["crop_config_json"]
        new_caption = json.dumps(payload.caption_config) if payload.caption_config is not None else r["caption_config_json"]
        
        await db.execute(
            """
            UPDATE clips
            SET title = ?, start_time = ?, end_time = ?, duration = ?, crop_config_json = ?, caption_config_json = ?, status = 'edited'
            WHERE id = ?
            """,
            (new_title, new_start, new_end, new_duration, new_crop, new_caption, clip_id)
        )
        await db.commit()
        
    return await get_clip(clip_id)
