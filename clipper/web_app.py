import os
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from clipper.config import BASE_DIR, OUTPUT_DIR

app = FastAPI(title="Opus Clip AI Dashboard")

WEB_DIR = BASE_DIR / "web"
REPORT_PATH = OUTPUT_DIR / "analysis_report.json"


class ProcessRequest(BaseModel):
    input_source: str
    top_n: int = 3
    min_duration: float = 15.0
    max_duration: float = 90.0


@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index HTML not found")
    return index_file.read_text(encoding="utf-8")


@app.get("/api/report")
async def get_report():
    if not REPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="No analysis report found yet. Run the pipeline first.")
    try:
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video/{clip_id}")
async def get_clip_video(clip_id: int):
    if not REPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    clips = data.get("clips", [])
    target = next((c for c in clips if c.get("id") == clip_id), None)

    if not target or not target.get("exported_file"):
        raise HTTPException(status_code=404, detail=f"No exported video found for clip #{clip_id}")

    video_path = Path(target["exported_file"])
    if not video_path.exists():
        # Check if file exists in OUTPUT_DIR with the same name
        alt_path = OUTPUT_DIR / video_path.name
        if alt_path.exists():
            video_path = alt_path
        else:
            raise HTTPException(status_code=404, detail=f"Video file missing on disk: {video_path.name}")

    return FileResponse(path=str(video_path), media_type="video/mp4", filename=video_path.name)


@app.post("/api/process")
async def process_video_endpoint(req: ProcessRequest):
    from clipper.pipeline import run_pipeline

    try:
        report = run_pipeline(
            input_source=req.input_source,
            top_n=req.top_n,
            min_duration=req.min_duration,
            max_duration=req.max_duration
        )
        return {"status": "ok", "report": report}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def start_server(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    print(f"\n[+] Starting Opus Clip Local Dashboard at: http://{host}:{port}")
    uvicorn.run("clipper.web_app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start_server()
