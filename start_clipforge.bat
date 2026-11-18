@echo off
title ClipForge Studio Launcher
echo ========================================================
echo   CLIPFORGE - Local AI Video Repurposing Studio
echo ========================================================
echo Starting FastAPI backend and Next.js frontend...
.venv\Scripts\python.exe scripts\run_clipforge.py
pause
