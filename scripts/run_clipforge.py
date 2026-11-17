"""
ClipForge Local Launcher
Runs both the FastAPI backend and Next.js frontend simultaneously for local development.
"""
import sys
import subprocess
import time
import signal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PYTHON_EXE = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
FRONTEND_DIR = ROOT_DIR / "frontend"

def main():
    print("=" * 60)
    print("  CLIPFORGE — Local AI Video Repurposing Studio")
    print("=" * 60)
    
    # 1. Start Backend
    print("[1/2] Starting FastAPI backend on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [
            str(PYTHON_EXE),
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
        ],
        cwd=str(ROOT_DIR),
    )
    
    time.sleep(2)
    
    # 2. Start Frontend
    print("[2/2] Starting Next.js studio frontend on http://localhost:3000 ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )
    
    print("\n" + "=" * 60)
    print("  ClipForge is LIVE!")
    print("  Website:  http://localhost:3000")
    print("  API Docs: http://localhost:8000/docs")
    print("  Press Ctrl+C to terminate both servers.")
    print("=" * 60 + "\n")
    
    def shutdown(sig, frame):
        print("\nShutting down ClipForge servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == "__main__":
    main()
